from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    class Meta:
        unique_together = ('owner', 'name')  # a user can't have two categories with the same name
        ordering = ['name']  # default order: A-Z
    def __str__(self):
        return self.name

class Income(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    class Meta:
        ordering = ['-date', '-id'] # newest first; -id breaks ties between same-day entries

class Expense(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)
    # PROTECT: a category that still has expenses can't be deleted
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    description = models.TextField(max_length=200, blank=True)
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    class Meta:
        ordering = ['-date', '-id']  