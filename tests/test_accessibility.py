"""
Accessibility smoke tests for all static HTML pages.

Parses each HTML file with BeautifulSoup and checks for common a11y issues:
- img tags must have alt attributes
- buttons must have accessible text (textContent or aria-label)
- skip links must exist on user-facing pages
- forms must have associated labels
- icons used decoratively must have aria-hidden="true"
- navbar toggler buttons must have required ARIA attributes
"""

import os
import glob

import pytest
from bs4 import BeautifulSoup

STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'static')

SKIP_PAGES = {'test-error-handling.html'}

REDIRECT_PAGES = {'commute.html'}


def get_html_files():
    """Return list of (filename, parsed soup) for all static HTML pages."""
    pattern = os.path.join(STATIC_DIR, '*.html')
    files = []
    for filepath in sorted(glob.glob(pattern)):
        filename = os.path.basename(filepath)
        if filename in SKIP_PAGES:
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        files.append((filename, soup))
    return files


HTML_FILES = get_html_files()


@pytest.mark.unit
class TestImageAccessibility:
    """All img tags must have alt attributes."""

    @pytest.mark.parametrize('filename,soup', HTML_FILES, ids=[f[0] for f in HTML_FILES])
    def test_images_have_alt(self, filename, soup):
        images = soup.find_all('img')
        for img in images:
            assert img.has_attr('alt'), (
                f'{filename}: <img> tag missing alt attribute: {img}'
            )


@pytest.mark.unit
class TestButtonAccessibility:
    """All buttons must have accessible text via textContent or aria-label."""

    @pytest.mark.parametrize('filename,soup', HTML_FILES, ids=[f[0] for f in HTML_FILES])
    def test_buttons_have_accessible_text(self, filename, soup):
        buttons = soup.find_all('button')
        for button in buttons:
            has_aria_label = button.has_attr('aria-label')
            text_content = button.get_text(strip=True)
            has_text = bool(text_content)
            assert has_aria_label or has_text, (
                f'{filename}: <button> missing accessible text: {button}'
            )


@pytest.mark.unit
class TestSkipLinks:
    """User-facing pages must have skip-to-main-content links."""

    @pytest.mark.parametrize('filename,soup', HTML_FILES, ids=[f[0] for f in HTML_FILES])
    def test_skip_link_present(self, filename, soup):
        if filename in REDIRECT_PAGES:
            pytest.skip(f'{filename} is a redirect page')

        skip_links = soup.find_all('a', class_='skip-link')
        assert len(skip_links) > 0, (
            f'{filename}: missing skip-link (<a class="skip-link">)'
        )

        targets = [link.get('href', '') for link in skip_links]
        assert any(t == '#main-content' for t in targets), (
            f'{filename}: skip-link does not target #main-content, found: {targets}'
        )

    @pytest.mark.parametrize('filename,soup', HTML_FILES, ids=[f[0] for f in HTML_FILES])
    def test_main_content_target_exists(self, filename, soup):
        if filename in REDIRECT_PAGES:
            pytest.skip(f'{filename} is a redirect page')

        main_el = soup.find(id='main-content')
        assert main_el is not None, (
            f'{filename}: skip-link target #main-content not found in page'
        )


@pytest.mark.unit
class TestFormLabels:
    """Form inputs (text, select, etc.) must have associated labels."""

    LABELABLE_TYPES = {
        'text', 'password', 'email', 'number', 'tel', 'url',
        'search', 'date', 'time', 'datetime-local', 'file',
    }

    @pytest.mark.parametrize('filename,soup', HTML_FILES, ids=[f[0] for f in HTML_FILES])
    def test_inputs_have_labels(self, filename, soup):
        inputs = soup.find_all('input')
        for inp in inputs:
            input_type = inp.get('type', 'text').lower()
            if input_type in ('hidden', 'submit', 'button', 'reset', 'checkbox', 'radio'):
                continue
            if input_type not in self.LABELABLE_TYPES:
                continue

            input_id = inp.get('id')
            has_label = False
            if input_id:
                label = soup.find('label', attrs={'for': input_id})
                if label:
                    has_label = True
            if inp.has_attr('aria-label'):
                has_label = True
            if inp.has_attr('aria-labelledby'):
                has_label = True

            assert has_label, (
                f'{filename}: <input type="{input_type}" id="{input_id}"> '
                f'missing associated <label> or aria-label'
            )

    @pytest.mark.parametrize('filename,soup', HTML_FILES, ids=[f[0] for f in HTML_FILES])
    def test_selects_have_labels(self, filename, soup):
        selects = soup.find_all('select')
        for sel in selects:
            sel_id = sel.get('id')
            has_label = False
            if sel_id:
                label = soup.find('label', attrs={'for': sel_id})
                if label:
                    has_label = True
            if sel.has_attr('aria-label'):
                has_label = True
            if sel.has_attr('aria-labelledby'):
                has_label = True

            assert has_label, (
                f'{filename}: <select id="{sel_id}"> '
                f'missing associated <label> or aria-label'
            )


@pytest.mark.unit
class TestDecorativeIcons:
    """Bootstrap Icons used next to text should have aria-hidden="true"."""

    @pytest.mark.parametrize('filename,soup', HTML_FILES, ids=[f[0] for f in HTML_FILES])
    def test_nav_icons_are_decorative(self, filename, soup):
        nav = soup.find('nav', attrs={'aria-label': 'Main navigation'})
        if not nav:
            pytest.skip(f'{filename} has no main navigation')

        icons = nav.find_all('i', class_=lambda c: c and 'bi' in c.split())
        for icon in icons:
            assert icon.get('aria-hidden') == 'true', (
                f'{filename}: nav icon missing aria-hidden="true": {icon}'
            )


@pytest.mark.unit
class TestNavbarToggler:
    """Navbar toggler buttons must have ARIA controls and labels."""

    @pytest.mark.parametrize('filename,soup', HTML_FILES, ids=[f[0] for f in HTML_FILES])
    def test_toggler_has_aria_attributes(self, filename, soup):
        toggler = soup.find('button', class_='navbar-toggler')
        if not toggler:
            pytest.skip(f'{filename} has no navbar toggler')

        assert toggler.has_attr('aria-controls'), (
            f'{filename}: navbar-toggler missing aria-controls'
        )
        assert toggler.has_attr('aria-expanded'), (
            f'{filename}: navbar-toggler missing aria-expanded'
        )
        assert toggler.has_attr('aria-label'), (
            f'{filename}: navbar-toggler missing aria-label'
        )


@pytest.mark.unit
class TestLangAttribute:
    """Every page must declare a language on the html element."""

    @pytest.mark.parametrize('filename,soup', HTML_FILES, ids=[f[0] for f in HTML_FILES])
    def test_html_has_lang(self, filename, soup):
        html_tag = soup.find('html')
        assert html_tag is not None, f'{filename}: no <html> tag found'
        assert html_tag.has_attr('lang'), (
            f'{filename}: <html> tag missing lang attribute'
        )
        assert html_tag['lang'].strip(), (
            f'{filename}: <html lang=""> is empty'
        )
