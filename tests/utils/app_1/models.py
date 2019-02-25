from django.db import models


class App1Post(models.Model):
    pass


class App1PostContent(models.Model):
    post = models.ForeignKey(App1Post, on_delete=models.CASCADE)

    def get_absolute_url(self):
        return "/"


class App1Title(models.Model):
    pass


class App1TitleContent(models.Model):
    title = models.ForeignKey(App1Title, on_delete=models.CASCADE)

    def get_absolute_url(self):
        return "/"


class App1NonModeratedModel(models.Model):
    pass
