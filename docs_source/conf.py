import logging

project = 'Pycommence'
author = 'PawRequest'
release = '0.1.1'
copyright = f'2024, {author}'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.linkcode',
    'myst_parser',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.githubpages',
    'sphinx_autodoc_typehints',
    'sphinx_readme',
    'sphinx_rtd_dark_mode',
]
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
master_doc = 'README'

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_css_files = ['custom.css']

html_context = {
    "display_github": True,
    "github_user": "PawRequest",
    "github_repo": "pycommence",
    "github_version": "main",
    "conf_py_path": "/docs_source/",
}
html_baseurl = 'https://pawrequest.github.io/pycommence/'
readme_src_files = 'README.rst'
readme_docs_url_type = 'code'
add_module_names = False
autodoc_default_options = {
    'exclude-members': 'model_config, model_fields, model_computed_fields',
    'members': True,
    'member-order': 'bysource',
    'undoc-members': True,
}

repo_src = 'https://github.com/pawrequest/pycommence/blob/main/src'


def linkcode_resolve(domain, info):
    if domain != 'py':
        return None
    if not info['module']:
        return None

    filename = info['module'].replace('.', '/')
    url = f'{repo_src}/{filename}.py'
    return url
