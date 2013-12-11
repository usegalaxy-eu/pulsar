from os.path import join
from os import makedirs, system
from six import next, itervalues
from .test_utils import TempDirectoryTestCase, skipUnlessExecutable, skipUnlessModule

from lwr.util.bunch import Bunch
from .check import run
try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser


class BaseIntegrationTest(TempDirectoryTestCase):

    def _run(self, app_conf={}, job_conf_props={}, **kwds):
        app_conf = app_conf.copy()
        job_conf_props = job_conf_props.copy()

        if "suppress_output" not in kwds:
            kwds["suppress_output"] = False

        self.__setup_job_properties(app_conf, job_conf_props)
        self.__setup_dependencies(app_conf)

        if kwds.get("direct_interface", None):
            from .test_utils import test_app
            with test_app({}, app_conf, {}) as app:
                options = Bunch(job_manager=next(itervalues(app.app.managers)), file_cache=app.app.file_cache, **kwds)
                run(options)
        else:
            from .test_utils import test_server
            with test_server(app_conf=app_conf) as server:
                options = Bunch(url=server.application_url, **kwds)
                run(options)

    def __setup_job_properties(self, app_conf, job_conf_props):
        if job_conf_props:
            job_conf = join(self.temp_directory, "job_managers.ini")
            config = ConfigParser()
            section_name = "manager:_default_"
            config.add_section(section_name)
            for key, value in job_conf_props.iteritems():
                config.set(section_name, key, value)
            with open(job_conf, "wb") as configf:
                config.write(configf)

            app_conf["job_managers_config"] = job_conf

    def __setup_dependencies(self, app_conf):
        dependencies_dir = join(self.temp_directory, "dependencies")
        dep1_directory = join(dependencies_dir, "dep1", "1.1")
        makedirs(dep1_directory)
        try:
            # Let external users read/execute this directory for run as user
            # test.
            system("chmod 755 %s" % self.temp_directory)
            system("chmod -R 755 %s" % dependencies_dir)
        except Exception as e:
            print e
        env_file = join(dep1_directory, "env.sh")
        with open(env_file, "w") as env:
            env.write("MOO=moo_override; export MOO")
        app_conf["tool_dependency_dir"] = dependencies_dir


class IntegrationTests(BaseIntegrationTest):
    default_kwargs = dict(direct_interface=False, test_requirement=True)

    def test_integration_no_requirement(self):
        self._run(private_token=None, **self.default_kwargs)

    @skipUnlessModule("drmaa")
    def test_integration_as_user(self):
        job_props = {'type': 'queued_external_drmaa', "production": "false"}
        self._run(job_conf_props=job_props, private_token=None, default_file_action="copy", user='u1', **self.default_kwargs)

    def test_integration_copy(self):
        self._run(private_token=None, default_file_action="copy", **self.default_kwargs)

    def test_integration_no_transfer(self):
        self._run(private_token=None, default_file_action="none", **self.default_kwargs)

    def test_integration_cached(self):
        self._run(private_token=None, cache=True, **self.default_kwargs)

    def test_integration_default(self):
        self._run(private_token=None, **self.default_kwargs)

    @skipUnlessModule("pycurl")
    def test_integration_curl(self):
        self._run(private_token=None, transport="curl", **self.default_kwargs)

    def test_integration_token(self):
        self._run(app_conf={"private_key": "testtoken"}, private_token="testtoken", **self.default_kwargs)

    def test_integration_errors(self):
        self._run(app_conf={"private_key": "testtoken"}, private_token="testtoken", test_errors=True, **self.default_kwargs)

    @skipUnlessModule("drmaa")
    def test_integration_drmaa(self):
        self._run(app_conf={}, job_conf_props={'type': 'queued_drmaa'}, private_token=None, **self.default_kwargs)

    @skipUnlessExecutable("condor_submit")
    def test_integration_condor(self):
        self._run(app_conf={}, job_conf_props={'type': 'queued_condor'}, private_token=None, **self.default_kwargs)

    @skipUnlessExecutable("qsub")
    def test_integration_cli(self):
        self._run(app_conf={}, job_conf_props={'type': 'queued_cli', 'job_plugin': 'Torque'}, private_token=None, **self.default_kwargs)


class DirectIntegrationTests(IntegrationTests):
    default_kwargs = dict(direct_interface=True, test_requirement=False)
