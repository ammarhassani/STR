"""
Write Queue Manager for Concurrent Database Operations
Processes write operations sequentially to prevent conflicts
"""
import queue
import threading
import time
from typing import Callable, Optional, Tuple


class WriteQueue:
    """Manages sequential write operations to prevent database conflicts"""
    
    def __init__(self, db_manager):
        """
        Initialize write queue
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.queue = queue.Queue()
        self.db_manager = db_manager
        self.is_running = True
        
        # Start background worker thread
        self.worker_thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
            name="WriteQueueWorker"
        )
        self.worker_thread.start()
    
    def _process_queue(self):
        """Process write operations sequentially in background thread"""
        while self.is_running:
            try:
                # Get operation from queue (blocks with timeout)
                operation = self.queue.get(timeout=1.0)
                
                # Unpack operation
                query, params, callback, error_callback = operation
                
                try:
                    # Execute with retry logic
                    result = self.db_manager.execute_with_retry(query, params)
                    
                    # Call success callback if provided
                    if callback:
                        try:
                            callback(result)
                        except Exception as e:
                            print(f"Callback error: {e}")
                            
                except Exception as e:
                    # Call error callback if provided
                    if error_callback:
                        try:
                            error_callback(e)
                        except Exception as cb_error:
                            print(f"Error callback failed: {cb_error}")
                    else:
                        print(f"Queue processing error: {e}")
                
                finally:
                    self.queue.task_done()
                    
            except queue.Empty:
                # No operations in queue, continue waiting
                continue
            except Exception as e:
                print(f"Unexpected queue error: {e}")
    
    def submit(
        self,
        query: str,
        params: tuple = (),
        callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None
    ) -> None:
        """
        Submit write operation to queue
        
        Args:
            query: SQL query (INSERT, UPDATE, DELETE)
            params: Query parameters
            callback: Function to call on success (receives result)
            error_callback: Function to call on error (receives exception)
        """
        self.queue.put((query, params, callback, error_callback))
    
    def submit_and_wait(
        self,
        query: str,
        params: tuple = ()
    ) -> Optional[list]:
        """
        Submit write operation and wait for completion
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Query result or None if error
        """
        result_container = {'result': None, 'error': None}
        event = threading.Event()
        
        def success_callback(result):
            result_container['result'] = result
            event.set()
        
        def error_callback(error):
            result_container['error'] = error
            event.set()
        
        self.submit(query, params, success_callback, error_callback)
        
        # Wait for completion (with timeout)
        event.wait(timeout=30.0)
        
        if result_container['error']:
            raise result_container['error']
        
        return result_container['result']
    
    def wait_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Block until all queued operations are complete
        
        Args:
            timeout: Maximum time to wait in seconds (None = infinite)
            
        Returns:
            True if all operations completed, False if timeout
        """
        if timeout:
            start_time = time.time()
            while not self.queue.empty():
                if time.time() - start_time > timeout:
                    return False
                time.sleep(0.1)
            return True
        else:
            self.queue.join()
            return True
    
    def get_queue_size(self) -> int:
        """Get number of pending operations in queue"""
        return self.queue.qsize()
    
    def stop(self, wait_for_completion: bool = True) -> None:
        """
        Stop queue processing
        
        Args:
            wait_for_completion: If True, wait for pending operations to complete
        """
        if wait_for_completion:
            self.wait_completion()
        
        self.is_running = False
        self.worker_thread.join(timeout=5.0)
