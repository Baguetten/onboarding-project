from django.utils.timezone import localdate
from rest_framework import serializers
from finance.models import Category, Income, Expense

class CategorySerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = Category
        fields = ['id', 'name', 'owner']
    def validate_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Category name must be at least 3 characters long.")
        elif Category.objects.filter(owner=self.context['request'].user, name__iexact=value).exists():
            raise serializers.ValidationError("A category with this name already exists.")
        return value

class ExpenseSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = Expense
        fields = ['id', 'amount', 'date', 'category', 'description', 'owner']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            self.fields['category'].queryset = Category.objects.filter(owner=request.user)

    def validate(self, data):
       if data.get('amount', 0) > 50 and data.get('description', '') == '':
           raise serializers.ValidationError("Description is required for expenses over 50.")
       return data

    def validate_category(self, value):
        if value.owner != self.context['request'].user:
            raise serializers.ValidationError("You can only assign expenses to your own categories.")   
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be a positive number.")
        return value

    def validate_description(self, value):
        if 0 < len(value.strip()) < 3: #Allows empty descriptions but requires at least 3 characters if provided
            raise serializers.ValidationError("Description must be at least 3 characters long.")
        return value

    def validate_date(self, value):
        if value > localdate():
            raise serializers.ValidationError("Date cannot be in the future.")
        return value

class IncomeSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = Income
        fields = ['id', 'amount', 'date', 'owner']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be a positive number.")
        return value

    def validate_date(self, value):
        if value > localdate():
            raise serializers.ValidationError("Date cannot be in the future.")
        return value