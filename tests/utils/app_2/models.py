from django.db import models


class App2Post(models.Model):
    pass


class App2PostContent(models.Model):
    post = models.ForeignKey(App2Post, on_delete=models.CASCADE)


class App2Title(models.Model):
    pass


class App2TitleContent(models.Model):
    title = models.ForeignKey(App2Title, on_delete=models.CASCADE)
