from django.apps import AppConfig


class App2Config(AppConfig):
    name = "tests.utils.app_2"
    label = "app_2"
    verbose_name = "Another django app with cms_config for integration test"
