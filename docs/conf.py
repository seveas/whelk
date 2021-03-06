import sphinx_rtd_theme as theme
source_suffix = '.rst'
master_doc = 'index'
project = u'whelk'
copyright = u'2010-2020, Dennis Kaarsemaker'
version = '3.0'
release = '3.0'
pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'roottarget': 'index',
    'stickysidebar': False,
}
html_theme_path = [theme.get_html_theme_path()]
html_show_sourcelink = False
html_show_sphinx = False
