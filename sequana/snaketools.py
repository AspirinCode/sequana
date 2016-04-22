"""Set of tools to manipulate Snakefile and config files

Here is an overview (see details here below)

.. autosummary::
    :nosignatures:

    sequana.snaketools.DOTParser
    sequana.snaketools.ExpandedSnakeFile
    sequana.snaketools.Module
    sequana.snaketools.ModuleNames
    sequana.snaketools.SnakeMakeProfile
    sequana.snaketools.SnakeMakeStats
    sequana.snaketools.SequanaConfig
    sequana.snaketools.get_cleanup_rules
    sequana.snaketools.get_tagname
    sequana.snaketools.message
    sequana.snaketools.modules


"""
import os
import sys
import json
import glob
from os.path import isdir

from easydev import get_package_location as gpl
from easydev import load_configfile, AttrDict

import pandas as pd
import pylab


#__all__ = ["SequanaConfig"]

try:
    # This is for python2.7
    import snakemake
except:
    print("Snakemake must be installed. Available for Python3 only")
    class MockSnakeMake(object):
        def __init__(self):
            pass
        def Workflow(self, filename):
            raise ImportError
    snakemake = MockSnakeMake()




class ExpandedSnakeFile(object):
    """Read a Snakefile and its dependencies (include) and create single file

    **Motivation**

    a Snakefile may look like::

        from sequana import snaketools as sm
        include: sm.modules['bwa_phix']
        include: sm.modules['fastqc']

    This is nice and compact but we do not see anymore what the Snakefile does.
    This class will recreate the Snakefile without this compactness so that one
    can see the entire structure. The expansion is performed by :meth:`expand`.

    .. warning:: experimental. docstrings should be removed. lines starting 
        with **include** should also be removed.

    """
    def __init__(self, snakefile):
        # read the file and include it (Snakemake API)
        # This import is the package not the sequana.snaketools file
        self.snakefile = snakemake.Workflow(snakefile)
        self.snakefile.include(snakefile)

    def expand(self, output_filename="Snakefile.expanded"):
        """The expansion of Snakefile

        :param str filename: name of the output file

        """
        # open a file to save all included rules and workflow in one place
        with open(output_filename, "w") as workflow_expanded:
            # scan all included workflow
            for include in self.snakefile.included:
                with open(include, "r") as wk_toinclude:
                    data = wk_toinclude.read()
                    workflow_expanded.write(data)


class SnakeMakeProfile(object):
    """Interpret the snakemake profile file

    Run the Snakemake with this option::

        --profile profile.json

    """
    def __init__(self, filename):
        self.filename = filename

    def parse(self):
        data = json.loads(self.filename)


class SnakeMakeStats(object):
    """Interpret the snakemake stats file 

    Run the Snakemake with this option::

        -- stats stats.txt

    Then:

    .. plot::
        :include-source:

        from sequana.snaketools import SnakeMakeStats
        from sequana import sequana_data
        filename = sequana_data("test_snakemake_stats.txt", "testing")
        s = SnakeMakeStats(filename)
        s.plot()

    """
    def __init__(self, filename):
        """.. rubric:: Cosntructor"""
        self.filename = filename

    def _parse_data(self):
        with open(self.filename, 'r') as fin:
            data = json.load(fin)
        return data

    def plot(self, fontsize=16):
        """Create the barplot from the stats file"""
        pylab.clf()
        df = pd.DataFrame(self._parse_data()['rules'])
        ts = df.ix['mean-runtime']
        ts['total'] = self._parse_data()['total_runtime']
        ts.sort_values(inplace=True)

        ts.plot.barh(fontsize=fontsize)
        pylab.grid(True)
        pylab.xlabel("Seconds (s)", fontsize=fontsize)
        try:pylab.tight_layout()
        except:pass


class ModuleNames(object):
    """Data structure to hold the :class:`Module` names"""
    def __init__(self, extra_paths=[]):
        """.. rubric:: constructor

        :param list extra_paths: 


        .. doctest::

            >>> from sequana import ModuleNames
            >>> modnames = ModuleNames()
            >>> modnames.isvalid('dag')
            True
            >>> modnames.isvalid('dummy')
            False

        """
        self._module_paths = ['rules', 'pipelines']
        self._module_paths += extra_paths

        # names for eacj directory
        self._names = {}
        self._paths = {}

        # scan the paths
        for path in self._module_paths:
            self._add_names(path)

    def _add_names(self, path):
        sepjoin = os.sep.join
        fullpath = sepjoin([gpl("sequana"), "sequana", path])
        # just an alias
        isdir_alias = lambda x: isdir(sepjoin([fullpath, x]))

        # Finds all modules (directories)
        toignore = ['__pycache__']
        names = [this for this in os.listdir(fullpath) if isdir_alias(this)
                and this not in toignore]
        for name in names:
            if name in self._paths.keys():
                raise ValueError("Found duplicated name %s " % name)
            self._paths[name] = fullpath + os.sep + name

    def _get_names(self):
        return sorted(list(self._paths.keys()))
    names= property(_get_names, doc="list of existing module names")

    def isvalid(self, name):
        """Check that a name is an existing and valid module"""
        if name not in self.names:
            return False
        return True


class Module(object):
    """Data structure that holds metadata about a **Module**

    A **Module** in sequana's parlance is a directory that contains 
    the following files:

        - a **snakemake** file named **Snakefile** (although other naming
          conventions are accepted as explained below)
        - a **README.rst** file in restructured text format 
        - a config file in YAML format. Although json format is possible, 
          we use YAML throughout **sequana** for consistency.

    The name of the module is the name of the directory where the files are
    stored. The **Modules** are stored in sequana/rules and sequana/pipelines
    directories.

    The Snakefile may be named **Snakefile** or **Snakefile.<tag>** or
    **<module_name>.rules**.

    Before explaining the different type of **Modules**, let us remind
    that a **rule** in **Snakemake** terminology looks like::

        rule <name>:
            :input: file1
            :output: file2
            :shell: "cp file1 file2"

    However, in **sequana**, we speak of **Rules** with a different meaning. 
    Indeed, **Modules** are sub-divided into **Rules** and **Modules** defined
    as follows:

        - if the **Snakefile** includes other **Snakefile** then
          we consider that that Module is a **Pipeline**.
        - if the **Snakefile** does not include other **Snakefile** and
          all internal snakemake rules start with the same name, we consider
          that that module is a **Rule** module. 

    This data structure ease the retrieval of metadata for the **Modules**
    stored in **sequana**. 

    """
    def __init__(self, name):
        name_validator = ModuleNames()
        name_validator.isvalid(name)
        self._path = name_validator._paths[name]
        self._name = name

        # could look into ./rules or ./pipelines
        self._snakefile = None
        self._description = None

    def _get_file(self, name):
        filename = self._path + os.sep + name
        if os.path.exists(filename):
            return filename

    def __str__(self):
        txt = "Rule **" + self.name + "**:\n" + self.description
        return txt

    def _get_path(self):
        return self._path
    path = property(_get_path, doc="full path to the module directory")

    def _get_config(self):
        filename = self._get_file("config.yaml")
        if filename is None:
            filename = self._get_file("config.yaml.optional")
        return filename
    config = property(_get_config, 
        doc="full path to the config file of the module")

    def _get_readme(self):
        return self._get_file("README.rst")
    readme = property(_get_readme,
        doc="full path to the README file of the module")

    def _get_snakefile(self):
        if self._snakefile is not None:
            return self._snakefile

        if self._get_file("Snakefile"):
            self._snakefile = self._get_file("Snakefile")
        elif self._get_file("Snakefile." + self.name):
            self._snakefile = self._get_file("Snakefile." + self.name)
        elif self._get_file(self.name + '.rules'):
            self._snakefile = self._get_file(self.name + ".rules")
        else:
            print("Snakefile for %s not found" % self.name)
        return self._snakefile
    snakefile = property(_get_snakefile,
        doc="full path to the Snakefile file of the module")

    def _get_name(self):
        return self._name
    name = property(_get_name, doc="name of the module")

    def _get_description(self):
        try:
            with open(self.readme) as fh:
                self._description = fh.read()
        except:
                self._description = "no description"
        return self._description
    description = property(_get_description, 
        doc="""Content of the README file associated with the module. 

::

    from sequana import Module
    m = Module('dag')
    print(m.description)

""")

    def onweb(self):
        #TOD: automatic switch
        from easydev import onweb
        if "rules" in self._path:
            onweb("http://github.com/sequana/sequana/tree/"
                  "master/sequana/rules/%s" % self.name)
        else:
            onweb("http://github.com/sequana/sequana/tree/"
                  "master/sequana/pipelines/%s" % self.name)



def _get_modules_snakefiles():
    modules = {}
    for name in ModuleNames().names:
        if Module(name).snakefile:
            modules[name] = Module(name).snakefile
    return modules

#: dictionary with module names as keys and fullpath to the Snakefile as values 
modules = _get_modules_snakefiles()


class SequanaConfig(object):
    """Reads YAML (or json) config file and ease access to its contents

    This can also be used to check the validity of the config file

    ::

        >>> vc = SequanaConfig(config)
        >>> config.e == 1
        True

    Input files should be stored into::

        samples:
            - file1: FILE1
            - file2: FILE2

    The second file may be optional. 

    :meth:`get_dataset_as_list`

    Empty strings in a config are interpreted as None but SequanaConfig will
    replace  None with empty strings, which is probably what was expected from
    the user. Similarly, in snakemake when settings the config file, one
    can override a value with a False but this is interepted as "False"
    This will transform back the "True" into True

    """
    def __init__(self, data, test_requirements=True, converts_none_to_str=True):
        """Could be a json or a yaml

        :param str filename: filename to a config file in json or yaml format.
        """
        if isinstance(data, str):
            config = load_configfile(data)
            self.config = AttrDict(**config)
        else:
            self.config = AttrDict(**data)

        if converts_none_to_str:
            #
            self._set_none_to_empty_string(self.config)

        self._converts_boolean(self.config)

        if test_requirements:
            requirements = ["samples", "samples:file1", "samples:file2", "project"]
            # converts to dictionary ?
            for this in requirements:
                this = this.split(":")[0]
                assert this in self.config.keys(),\
                    "Your config must contain %s" % this

        self.PROJECT = self.config.project
        self.DATASET = self.get_dataset_as_list()
        self.ff = FileFactory(self.DATASET)
        self.BASENAME = self.ff.basenames
        self.FILENAME = self.ff.filenames
        if len(self.DATASET) == 2:
            self.paired = True
        else:
            self.paired = False

    def _converts_boolean(self, subdic):
        for key,value in subdic.items():
            if isinstance(value, dict):
                subdic[key] = self._converts_boolean(value)
            else:
                if value in ['True', 'true', 'TRUE']:
                    subdic[key] = True
                if value in ['False', 'false', 'FALSE']:
                    subdic[key] = False
        return subdic
        
    def _set_none_to_empty_string(self, subdic):
        # recursively set parameter (None) to ""
        for key,value in subdic.items():
            if isinstance(value, dict):
                subdic[key] = self._set_none_to_empty_string(value)
            else:
                if value is None:
                    subdic[key] = ""
        return subdic

    @staticmethod
    def from_dict(dic):
        return SequanaConfig(dic)

    def get_dataset_as_list(self):
        filenames = []
        try:
            filenames.append(self.config.samples.file1)
            if self.config.samples.file2 != "":
                filenames.append(self.config.samples.file2)
        except:
            pass
        return filenames

    def check(self, requirements_dict):
        """a dcitionary in the form

        rule_name:["param1", ":param2", ":kwargs:N"]

        in a config::

        param1: 1
        param2:
            - subparam1
            - subparam2:
                - subparam3: 10


        """
        dd = requirements_dict
        correct = True

        # check that each field request is present
        for k, vlist in dd.items():
            k = k.replace('__sequana__', '')
            if k not in self.config.keys():
                raise KeyError("Expected section %s not found" % k)
            else:
                for item in vlist:
                    # with : , this means a sub field field 
                    if item.startswith(":") and item.count(":")==1:
                        assert item[1:] in self.config[k].keys()
                    elif item.count(":")>1:
                        raise NotImplementedError(
                        "2 hierarchy checks in config not implemented ")
                    else:
                        # without : , this means a normal field so item is
                        # actually a key here
                        assert item in self.config.keys()


def sequana_check_config(config, globs):
    s = SequanaConfig.from_dict(config)
    dic = dict([ (k,v) for k,v in globs.items() 
                    if k.startswith("__sequana__")])
    s.check(dic)



def message(mes):
    """Dedicated print function to include in Snakefiles

    In a Snakefile, the stand print function may interfer with other process
    An example is the creation of the dag file. Not sure this is a bug but
    meanwhile, one must use this function to print information.

    This adds the // -- characters in front of the prin statements."""
    from easydev.console import purple
    print("// -- " + purple(mes))


class DOTParser(object):
    """Utility to parse the dot returned by Snakemake and add URLs automatically

    ::

        from sequana import sequana_data
        from sequana.snaketools import DOTParser

        filename = sequana_data("test_dag.dot", "testing")
        dot = DOTParser(filename)

        # creates test_dag.ann.dot
        dot.add_urls()

    """
    def __init__(self, filename):
        self.filename = filename

    def add_urls(self):
        """Create a new dot file with clickable links.

        So far all boxes are clickable even though a HTML report is not created.

        .. todo:: introspect the modules to figure out if a report is
            available or not

        """
        with open(self.filename, "r") as fh:
            data = fh.read()

        with open(self.filename.replace(".dot", ".ann.dot"), "w") as fout:
            indices_to_drop = []
            for line in data.split("\n"):
                if "[label =" not in line:
                    if " -> " in line:
                        label = line.split(" -> ")[0].strip()
                        if label not in indices_to_drop:
                            fout.write(line + "\n")
                    else:
                        fout.write(line + "\n")
                else:
                    separator = "color ="
                    lhs, rhs = line.split(separator)
                    name = lhs.split("label =")[1]
                    name = name.replace(",","")
                    name = name.replace('"',"")
                    name = name.strip()
                    if "__" in name:
                        lhs = lhs.replace(name, name.split('__')[0])

                    if name in ['dag', 'conda']:
                        index = lhs.split("[")[0]
                        indices_to_drop.append(index.strip())
                    elif name in ['all', "bwa_bam_to_fastq"] or "dataset:" in name:
                        # redirect to the main page so nothing to do 
                        newline = lhs + separator + rhs
                        fout.write(newline + "\n")
                    else:
                        # redirect to another report
                        newline = lhs + ' URL="%s.html" target="_parent", ' % name
                        newline += separator + rhs
                        fout.write(newline + "\n")


def get_tagname(filename):
    """Given a fullpath name, remove extension and prefix and return the name

    ::

        test.txt
        test.txt.gz
        dir/test.txt
        dir/test.txt.gz

    all return "test"
    """
    import os
    # This should always work
    name = os.path.split(filename)[1].split('.', 1)[0]
    return name


class FileFactory(object):
    """

        ff = FileNameFactory("../*")
        ff.dataset

    special case if ends in .fastq.gz


    definition to use::

        >>> fullpath = /home/user/test/A.fastq.gz
        >>> dirname(fullpath)
        '/home/user/test'
        >>> basename(fullpath)
        'A.fastq.gz'
        >>> realpath(fullpath) # is .., expanded to /home/user/test
        >>> all_extensions
        "fastq.gz"
        >>> extensions
        ".gz"


    """
    def __init__(self, pattern):
        self.pattern = pattern
        if isinstance(pattern, str):
            self._glob = glob.glob(pattern)
        elif isinstance(pattern, list):
            self._glob = pattern[:]
        

    def _get_realpath(self):
        return [os.path.realpath(filename) for filename in self._glob]
    realpaths = property(_get_realpath)

    def _get_basenames(self):
        return [os.path.split(filename)[1] for filename in self._glob]
    basenames = property(_get_basenames)

    def rstrip(self, ext):
        return [filename.rstrip(ext) for filename in self.basenames]

    def _get_filenames(self):
        return [this.split(".")[0] for this in self.basenames]
    filenames = property(_get_filenames) 

    def _pathnames(self):
        pathnames = [os.path.split(filename)[0] for filename in self._glob]
        return pathnames
    pathnames = property(_pathnames)

    def _pathname(self):
        pathname = set(self.pathnames)
        if len(pathname) == 1:
            return list(pathname)[0] + os.sep
        else:
            raise ValueError("found more than one pathname")
    pathname = property(_pathname)

    def _get_extensions(self):
        filenames = [os.path.splitext(filename)[1] for filename in self._glob]
        return filenames
    extensions = property(_get_extensions)

    def _get_all_extensions(self):
        filenames = [this.split('.', 1)[1] if "." in this else "" for this in self.basenames]
        return filenames
    all_extensions = property(_get_all_extensions)


def get_cleanup_rules(filename):
    """Scan a Snakefile and its inclusion and returns rules ending in _cleanup"""
    s = snakemake.Workflow(filename)
    s.include(filename)
    names = [rule.name for rule in list(s.rules) if rule.name.endswith('_cleanup')]
    return names












