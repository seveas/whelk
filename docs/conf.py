import cloud_sptheme as csp
source_suffix = '.rst'
master_doc = 'index'
project = u'whelk'
copyright = u'2010-2014, Dennis Kaarsemaker'
version = '2.4'
release = '2.4'
pygments_style = 'sphinx'
html_theme = 'cloud'
html_theme_options = {
    'roottarget': 'index',
    'stickysidebar': False,
}
html_theme_path = [csp.get_theme_dir()]
html_show_sourcelink = False
html_show_sphinx = False
