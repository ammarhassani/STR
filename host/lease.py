"""Single-row monotonic host term. The term is the failover coordination
primitive: a promoted host bumps it, and any other host that sees a higher
term (via the heartbeat) steps down. Stored in each host's LOCAL DB."""


def read_lease(db_manager):
    rows = db_manager.execute_with_retry("SELECT host_id, term FROM host_lease WHERE id = 1")
    if not rows:
        return (None, 0)
    return (rows[0][0], rows[0][1])


def bump_lease(db_manager, host_id, min_term=0):
    """Set term = max(current, min_term) + 1, record host_id, return new term.

    The increment is a single UPDATE so it is atomic: the statement takes the
    write lock and computes MAX() inside the engine, so two concurrent bumps
    serialize instead of both reading the same term and losing an increment.
    The read-back SELECT runs while that same transaction still holds the
    write lock, so it always sees this bump's value."""
    with db_manager.get_connection() as conn:
        conn.execute(
            "UPDATE host_lease SET term = MAX(term, ?) + 1, host_id = ?, "
            "updated_at = datetime('now') WHERE id = 1",
            (min_term, host_id))
        new_term = conn.execute("SELECT term FROM host_lease WHERE id = 1").fetchone()[0]
    return new_term
