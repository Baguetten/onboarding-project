from django.views import View
from rest_framework.authtoken.models import Token

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from finance.models import Category, Expense, Income
from finance.serializers import CategorySerializer, ExpenseSerializer, IncomeSerializer
from rest_framework import generics, permissions
from .permissions import IsOwner
from django.contrib.auth.mixins import LoginRequiredMixin
import requests

def api_call(request, path, method='get', **kwargs):
    token = Token.objects.get(user=request.user).key
    return requests.request(
        method,
        request.build_absolute_uri(path),
        headers={'Authorization': f'Token {token}'},
        **kwargs,
    )

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
        return render(request, self.template_name, self.context(request))

    def post(self, request):
        res = api_call(request, '/api/expenses/', 'post', data={
            'amount': request.POST['amount'],
            'category': request.POST['category'],
            'date': request.POST['date'],
            'description': request.POST['description'],
        })
        if res.status_code == 201:
            return redirect('expenses')
        return render(request, self.template_name, {**self.context(request), 'errors': res.json()})

    def context(self, request):
        return {
            'expenses': api_call(request, '/api/expenses/').json(),
            'categories': api_call(request, '/api/categories/').json(),
        }

class ExpenseDetailPageView(LoginRequiredMixin, View):
    template_name = 'expense_detail.html'

    def get(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk, owner=request.user)
        return render(request, self.template_name, {'expense': expense})
    
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