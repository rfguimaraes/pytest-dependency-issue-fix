"""pytest-dependency - Manage dependencies of tests

This pytest plugin manages dependencies of tests.  It allows to mark
some tests as dependent from other tests.  These tests will then be
skipped if any of the dependencies did fail or has been skipped.
"""

import setuptools
from setuptools import setup
import setuptools.command.build_py
import distutils.command.sdist
import distutils.file_util
from distutils import log
from glob import glob
import os
from pathlib import Path
from stat import ST_ATIME, ST_MTIME, ST_MODE, S_IMODE
import string
import subprocess
try:
    import distutils_pytest
    cmdclass = distutils_pytest.cmdclass
except (ImportError, AttributeError):
    cmdclass = dict()

def get_version_from_git():
    """Get version from git tags as a fallback."""
    try:
        # Determine the directory to run git from
        try:
            cwd = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            # __file__ not defined when exec'd directly
            cwd = os.getcwd()
        
        # Try to get version from git describe
        result = subprocess.run(
            ['git', 'describe', '--tags', '--always'],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd
        )
        git_version = result.stdout.strip()
        # Clean up the version string to be PEP 440 compliant
        # Replace any non-standard characters
        if git_version:
            return git_version.replace('-', '+', 1).replace('-', '.')
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

try:
    import gitprops
    release = str(gitprops.get_last_release())
    version = str(gitprops.get_version())
except (ImportError, LookupError):
    try:
        from _meta import release, version
    except ImportError:
        # Try to get version from git as a last resort
        git_version = get_version_from_git()
        if git_version:
            log.info("using version from git: %s", git_version)
            release = version = git_version
        else:
            log.warn("warning: cannot determine version number")
            # Use a valid placeholder version instead of UNKNOWN
            release = version = "0.0.0.dev0"

docstring = __doc__

class copy_file_mixin:
    """Distutils copy_file() mixin.

    Inject a custom version version of the copy_file() method that
    does some substitutions on the fly into distutils command class
    hierarchy.
    """
    Subst_srcs = {"src/pytest_dependency.py"}
    Subst = {'DOC': docstring, 'VERSION': version}
    def copy_file(self, infile, outfile,
                  preserve_mode=1, preserve_times=1, link=None, level=1):
        if infile in self.Subst_srcs:
            infile = Path(infile)
            outfile = Path(outfile)
            if outfile.name == infile.name:
                log.info("copying (with substitutions) %s -> %s",
                         infile, outfile.parent)
            else:
                log.info("copying (with substitutions) %s -> %s",
                         infile, outfile)
            if not self.dry_run:
                st = infile.stat()
                try:
                    outfile.unlink()
                except FileNotFoundError:
                    pass
                with infile.open("rt") as sf, outfile.open("wt") as df:
                    df.write(string.Template(sf.read()).substitute(self.Subst))
                if preserve_times:
                    os.utime(str(outfile), (st[ST_ATIME], st[ST_MTIME]))
                if preserve_mode:
                    outfile.chmod(S_IMODE(st[ST_MODE]))
            return (str(outfile), 1)
        else:
            if self.dry_run:
                return (outfile, 0)
            return distutils.file_util.copy_file(infile, outfile,
                                                 preserve_mode, preserve_times,
                                                 not self.force, link)

class meta(setuptools.Command):
    description = "generate meta files"
    user_options = []
    meta_template = '''
release = "%(release)s"
version = "%(version)s"
'''
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        version = self.distribution.get_version()
        log.info("version: %s", version)
        values = {
            'release': release,
            'version': version,
        }
        with Path("_meta.py").open("wt") as f:
            print(self.meta_template % values, file=f)

# Note: Do not use setuptools for making the source distribution,
# rather use the good old distutils instead.
# Rationale: https://rhodesmill.org/brandon/2009/eby-magic/
class sdist(copy_file_mixin, distutils.command.sdist.sdist):
    def run(self):
        self.run_command('meta')
        super().run()
        subst = {
            "version": self.distribution.get_version(),
            "url": self.distribution.get_url(),
            "description": docstring.split("\n")[0],
            "long_description": docstring.split("\n", maxsplit=2)[2].strip(),
        }
        for spec in glob("*.spec"):
            with Path(spec).open('rt') as inf:
                with Path(self.dist_dir, spec).open('wt') as outf:
                    outf.write(string.Template(inf.read()).substitute(subst))

class build_py(copy_file_mixin, setuptools.command.build_py.build_py):
    def run(self):
        self.run_command('meta')
        super().run()


with Path("README.rst").open("rt", encoding="utf8") as f:
    readme = f.read()

setup(
    name = "pytest-dependency",
    version = version,
    description = "Manage dependencies of tests",
    long_description = readme,
    long_description_content_type = "text/x-rst",
    url = "https://github.com/RKrahl/pytest-dependency",
    author = "Rolf Krahl",
    author_email = "rolf@rotkraut.de",
    license = "Apache-2.0",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
    ],
    project_urls = dict(
        Documentation="https://pytest-dependency.readthedocs.io/",
        Source="https://github.com/RKrahl/pytest-dependency",
        Download=("https://github.com/RKrahl/pytest-dependency/releases/%s/"
                  % release),
        Changes="https://pytest-dependency.readthedocs.io/en/latest/changelog.html",
    ),
    package_dir = {"": "src"},
    python_requires = ">=3.4",
    py_modules = ["pytest_dependency"],
    install_requires = ["setuptools", "pytest >= 3.7.0"],
    entry_points = {
        "pytest11": [
            "dependency = pytest_dependency",
        ],
    },
    cmdclass = dict(cmdclass, build_py=build_py, sdist=sdist, meta=meta),
)
