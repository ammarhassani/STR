"""Flat-enterprise theme unit checks. Run: python3.14 tests_theme.py"""
import sys
sys.path.insert(0, '/Users/engammar/Scripts/STR')
sys.path.insert(0, '/Users/engammar/Scripts/STR/flet_app')

FAILS = []
def check(name, ok, detail=''):
    print(('  ok  ' if ok else '  FAIL') + f' {name}' + ('' if ok else f' — {detail}'))
    if not ok: FAILS.append(name)

REQUIRED_KEYS = [
    'bg_primary','bg_secondary','bg_tertiary','bg_elevated',
    'text_primary','text_secondary','text_muted',
    'primary','primary_light','accent',
    'success','success_bg','warning','warning_bg','danger','danger_bg','info','info_bg',
    'border','border_light','hover','active','disabled',
    'card_bg','card_border','sidebar_bg','sidebar_item_hover','sidebar_item_active',
]

def test_tokens():
    from theme.colors import Colors
    p = Colors.get_palette('light')
    missing = [k for k in REQUIRED_KEYS if k not in p]
    check('T1 all required keys present', not missing, f'missing {missing}')
    check('T1 radius token added', p.get('radius') == 4, p.get('radius'))
    check('T1 teal accent kept', p['primary'] == '#0d7377', p['primary'])
    check('T1 light background is light', p['bg_primary'].lower() in ('#ffffff', '#f7f8fa'), p['bg_primary'])
    check('T1 muted approved green', p['success'] == '#2f855a', p['success'])

if __name__ == '__main__':
    test_tokens()
    print(f"\nTHEME FAILURES: {len(FAILS)}")
    sys.exit(1 if FAILS else 0)
