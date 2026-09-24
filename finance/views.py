from django.views import View
from rest_framework.authtoken.models import Token

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from finance.models import Category, Expense, Income
from finance.serializers import CategorySerializer, ExpenseSerializer, IncomeSerializer
from rest_framework import generics, permissions
from .permissions import IsOwner
from django.contrib.auth.mixins import LoginRequiredMixin

@login_required
def home(request):
    return render(request, 'home.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def create_account(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password != confirm_password:
            raise ValueError("Passwords do not match")

        user = User.objects.create_user(username=username, password=password)
        Token.objects.get_or_create(user=user)
        login(request, user)
        return redirect('home')
    return render(request, 'create_account.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            Token.objects.get_or_create(user=user)
            login(request, user)
            return redirect('home')
        else:
            raise ValueError("Invalid username or password")
    return render(request, 'login.html')

class ExpenseListCreateView(LoginRequiredMixin, View):
    template_name = 'expenses.html'
    def get(self, request):
        expenses = Expense.objects.filter(owner=request.user)
        categories = Category.objects.filter(owner=request.user)
        return render(request, self.template_name, {'expenses': expenses, 'categories': categories})
    def post(self, request):
        serializer = ExpenseSerializer(data=request.POST, context={'request': request})
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return redirect('expenses')
        return render(request, self.template_name, {
            'expenses': Expense.objects.filter(owner=request.user),
            'categories': Category.objects.filter(owner=request.user),
            'errors': serializer.errors,
        })

class CategoryListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CategorySerializer
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user)

class ExpenseListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ExpenseSerializer
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    def get_queryset(self):
        return Expense.objects.filter(owner=self.request.user)

class ExpenseDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    serializer_class = ExpenseSerializer
    def get_queryset(self):
        return Expense.objects.filter(owner=self.request.user)

class IncomeListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = IncomeSerializer
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    def get_queryset(self):
        return Income.objects.filter(owner=self.request.user)