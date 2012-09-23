"""
Testing for TG2 Configuration
"""
from nose import SkipTest
from nose.tools import eq_, raises
import atexit, sys

from tg.util import Bunch
from tg.configuration import AppConfig, config
from tg.configuration.app_config import TGConfigError
from tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir, create_request

from tg._compat import PY3


def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

class AtExitTestException(Exception):
    pass

class TestPylonsConfigWrapper:

    def setup(self):
        self.config = config

    def test_create(self):
        pass

    def test_getitem(self):
        expected_keys = ['global_conf', 'use_sqlalchemy', 'package', 'tg.app_globals', 'call_on_shutdown']
        for key in expected_keys:
            self.config[key]

    @raises(KeyError)
    def test_getitem_bad(self):
        self.config['no_such_key']

    def test_setitem(self):
        self.config['no_such_key'] = 'something'

    def test_delattr(self):
        del self.config.use_sqlalchemy
        eq_(hasattr(self.config, 'use_sqlalchemy'), False)
        self.config.use_sqlalchemy = True

    @raises(AttributeError)
    def test_delattr_bad(self):
        del self.config.i_dont_exist

class TestAppConfig:
    def __init__(self):
        class FakeAppGlobals(object):
            pass

        self.fake_package = Bunch({'__name__':'tests',
                                   '__file__':__file__,
                                   'lib':Bunch({'app_globals':Bunch({
                                                    'Globals':FakeAppGlobals})
                                               })
                                   })

    def setup(self):
        self.config = AppConfig()
        # set up some required paths and config settings
        # FIXME: these seem to be needed so that
        # other tests don't suffer - but that's a nasty
        # side-effect. setup for those tests actually needs
        # fixing.
        self.config.package = self.fake_package
        self.config['paths']['root'] = 'test'
        self.config['paths']['controllers'] = 'test'
        self.config.init_config({'cache_dir':'/tmp'}, {})

        config['paths']['static_files'] = "test"
        config["tg.app_globals"] = Bunch()
        config["use_sqlalchemy"] = False
        config["global_conf"] = Bunch()
        config["package"] = "test"
        config["call_on_shutdown"] = "foo"
        config["render_functions"] = Bunch()
        config['beaker.session.secret'] = 'some_secret'


    def test_create(self):
        pass

    def test_setup_startup_and_shutdown_startup_callable(self):
        def func():
            a = 7
        self.config.call_on_startup = [func]
        self.config.setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_callable_startup_with_exception(self):
        def func():
            raise Exception
        self.config.call_on_startup = [func]
        self.config.setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_startup_not_callable(self):
        self.config.call_on_startup = ['not callable']
        self.config.setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_shutdown_not_callable(self):
        self.config.call_on_shutdown = ['not callable']
        self.config.setup_startup_and_shutdown()

    @raises(AtExitTestException)
    def test_setup_startup_and_shutdown_shutdown_callable(self):
        def func():
            raise AtExitTestException()

        self.config.call_on_shutdown = [func]
        self.config.setup_startup_and_shutdown()
        atexit._run_exitfuncs()

    def test_setup_helpers_and_globals(self):
        self.config.setup_helpers_and_globals()

    def test_setup_sa_auth_backend(self):
        self.config.setup_sa_auth_backend()

    def test_setup_chameleon_genshi_renderer(self):
        if PY3: raise SkipTest()

        self.config.paths.templates = 'template_path'
        self.config.setup_chameleon_genshi_renderer()

    def test_setup_kajiki_renderer(self):
        if PY3: raise SkipTest()

        self.config.paths.templates = 'template_path'
        self.config.setup_kajiki_renderer()

    def test_setup_genshi_renderer(self):
        self.config.paths.templates = 'template_path'
        self.config.setup_genshi_renderer()

    def test_setup_jinja_renderer(self):
        self.config.paths.templates = 'template_path'
        self.config.setup_jinja_renderer()

    def test_setup_mako_renderer(self):
        self.config.paths.templates = ['template_path']
        self.config.setup_mako_renderer(use_dotted_templatenames=True)
    
    def test_setup_sqlalchemy(self):
        config['sqlalchemy.url'] = 'sqlite://'
        class Package:
            class model:
                @classmethod
                def init_model(package, engine):
                    pass
        self.config.package = Package()
        self.config.setup_sqlalchemy()

    def test_add_auth_middleware(self):
        class Dummy:pass

        self.config.sa_auth.dbsession = Dummy()
        self.config.sa_auth.user_class = Dummy
        self.config.sa_auth.group_class = Dummy
        self.config.sa_auth.permission_class = Dummy
        self.config.sa_auth.cookie_secret = 'dummy'
        self.config.sa_auth.password_encryption_method = 'sha'

        self.config.add_auth_middleware(None, None)

    def test_add_static_file_middleware(self):
        self.config.add_static_file_middleware(None)

    def test_register_hooks(self):
        def dummy(*args):
            pass

        self.config.register_hook('startup', dummy)
        self.config.register_hook('shutdown', dummy)
        self.config.register_hook('controller_wrapper', dummy)
        for hook_name in self.config.hooks.keys():
            self.config.register_hook(hook_name, dummy)

        for hooks in self.config.hooks.values():
            assert hooks

        assert self.config.call_on_startup
        assert self.config.call_on_shutdown
        assert self.config.controller_wrappers

    @raises(TGConfigError)
    def test_missing_secret(self):
        del config['beaker.session.secret']
        self.config.setup_sa_auth_backend()
