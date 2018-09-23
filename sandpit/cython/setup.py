from distutils.core import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize("create_gatling_scenario_graphs_cython.pyx")
)
