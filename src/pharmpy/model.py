"""
===================
Generic Model class
===================

**Base class of all implementations.**

Inherit to *implement*, i.e. to define support for a specific model type. Duck typing is utilized,
but an implementation is expected to implement **all** methods/attributes.

Definitions
-----------
"""

import copy
from pathlib import Path


class ModelException(Exception):
    pass


class ModelSyntaxError(ModelException):
    def __init__(self, msg='model syntax error'):
        super().__init__(msg)


class Model:
    """
     Property: name
    """
    @property
    def modelfit_results(self):
        return None

    def update_source(self):
        """Update the source"""
        self.source.code = str(self)

    def write(self, path='', force=False):
        """Write model to file using its source format
           If no path is supplied or does not contain a filename a name is created
           from the name property of the model
           Will not overwrite in case force is True.
           return path written to
        """
        path = Path(path)
        if not path or path.is_dir():
            try:
                filename = f'{self.name}{self.source.filename_extension}'
            except AttributeError:
                raise ValueError('Cannot name model file as no path argument was supplied and the'
                                 'model has no name.')
            path = path / filename
        if not force and path.exists():
            raise FileExistsError(f'File {path} already exists.')
        self.update_source(path=path, force=force)
        self.source.write(path, force=force)
        return path

    def update_inits(self):
        """Update inital estimates of model from its own ModelfitResults
        """
        if self.modelfit_results:
            self.parameters = self.modelfit_results.parameter_estimates
        else:
            # FIXME: Other exception here. ModelfitError?
            raise ModelException("Cannot update initial parameter estimates "
                                 "since parameters were not estimated")

    def copy(self):
        """Create a deepcopy of the model object"""
        return copy.deepcopy(self)

    def update_individual_estimates(self, source):
        self.initial_individual_estimates = self.modelfit_results.individual_estimates

#    Represents a model object, that may or may not exist on disk too.

#    Attributes:

#    .. note:: Attribute :attr:`path` always :class:`~pathlib.Path` object, but only resolved
#            (set to
#        absolute) by :attr:`exists`, which should be checked before any IO (read/write) on disk.
#        Thus, :attr:`path` needn't exist until needed!
#    """
    pass
#    SourceResource = SourceResource

#    Engine = Engine
#    """:class:`~pharmpy.execute.Engine` API.
#    Evaluation, estimation & simulation tasks."""

#    ModelInput = ModelInput
#    """:class:`~pharmpy.input.ModelInput` API.
#    E.g. data."""

#    _path = None
#    _index = 0

#    def __init__(self, path):
#        self.source = self.SourceResource(path)
#        self.input = self.ModelInput(self)
#        self.parameters = self.ParameterModel(self)
#        self.execute = self.Engine(self)
#        self.source.model = self

#    def validate(self):
#        """Test if model is syntactically valid (raises if not)."""
#        raise NotImplementedError

#    def write(self, path=None, exist_ok=True):
#        """Writes model to disk.

#        Will also update model to link that file.

#        Arguments:
#            path: A `path-like object`_ to write.
#            exist_ok: If False, :exc:`FileExistsError` is raised if the file already exists.

#        If no *path* given (default), model :attr:`path` attribute will be used. If not changed and
#        *exist_ok* (default), the model will be overwritten.

#        .. _path-like object: https://docs.python.org/3/glossary.html#term-path-like-object
#        """
#        path = path or self.path
#        if not path:
#            raise ValueError("No filesystem path set (can't write model)")
#        path = Path(path)
#        if path.exists and not exist_ok:
#            raise FileExistsError("Expected creating new file but path exists: %r" % str(path))
#        with open(str(path), 'w') as f:
#            f.write(str(self.source.output))
#        self.path = path.resolve()

#    @property
#    def has_results(self):
#        """True *if and only if* model has results.

#        .. todo::
#            Implement model execution/results status checker.
#            **Should** contain a call to :class:`.engine` class. An implementation of *that* should
#            then know how to check on current platform/cluster system (also *without*
#            initializing a
#            run directory).
#            **Shouldn't** need to override this (by implementation).
#        """
#        return True

#    def copy(self, dest=None, write=None):
#        """Returns a copy of this model.

#        Arguments:
#            dest: New filesystem path. If None, new :class:`Model` object retains previous
#                :attr:`~pharmpy.generic.Model.path`.
#            write: Write copy to disk (*dest* or previous :attr:`~pharmpy.generic.Model.path`).

#        By default, *write* is True if *dest* given and False otherwise.
#        """
#        model = deepcopy(self)
#        if dest:
#            model.path = dest
#            write = True if (write is None) else write
#        else:
#            write = False if (write is None) else write
#        if write:
#            model.write()
#        return model

#    def __repr__(self):
#        path = None if self.path is None else str(self.path)
#        return "%s(%r)" % (self.__class__.__name__, path)
