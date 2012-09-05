import cloud_sptheme as csp
source_suffix = '.rst'
master_doc = 'README'
project = u'whelk'
copyright = u'2010-2012, Dennis Kaarsemaker'
version = '1.0'
release = '1.0'
pygments_style = 'sphinx'
html_theme = 'cloud'
html_theme_options = {
    'roottarget': 'index',
    'stickysidebar': False,
}
html_theme_path = [csp.get_theme_dir()]
html_show_sourcelink = False
html_show_sphinx = False
