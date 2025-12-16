import re


def test_ui_layout_rules():
    css = open('static/css/style.css').read()
    # Ensure we have a responsive rule disabling sticky positioning on small screens
    assert re.search(r"@media\s*\(max-width:880px\)\s*\{[\s\S]*?\.form-card\s*\{[\s\S]*?position:\s*static", css), \
        'Expected .form-card { position: static } inside @media (max-width:880px) rule'

    # Ensure actions toolbar exists and stacks buttons on small screens
    assert re.search(r"\.actions-toolbar\s*\{[\s\S]*?display:\s*flex", css), 'Expected .actions-toolbar display:flex'
    assert re.search(r"@media\s*\(max-width:880px\)\s*\{[\s\S]*?\.actions-toolbar\s*\{[\s\S]*?flex-direction:\s*column", css), 'Expected actions toolbar to be column on small screens'