from django.views import View
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from finance.models import Category, Expense, Income
from finance.serializers import CategorySerializer, ExpenseSerializer, IncomeSerializer
from rest_framework import generics, permissions
from .permissions import IsOwner
from django.contrib.auth.mixins import LoginRequiredMixin
import requests
from django.http import Http404
from django.utils.timezone import localdate

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
        current_page = int(request.GET.get('page', 1))
        expenses_res =  api_call(request, '/api/expenses/', params={'page': current_page})
        categories_res = api_call(request, '/api/categories/')
        if expenses_res.status_code == 404 or categories_res.status_code == 404:
            raise Http404
        expenses_data = expenses_res.json()
        return {
            'expenses': expenses_data['results'],
            'categories': categories_res.json(),
            'current_page': current_page,
            'has_next': expenses_data['next'] is not None,
            'has_previous': expenses_data['previous'] is not None,
        }

class ExpenseDetailView(LoginRequiredMixin, View):
    template_name = "expense_detail.html"

    def get(self, request, pk):
        res = api_call(request, f'/api/expenses/{pk}/')
        if res.status_code == 404:
            raise Http404
        return render(request, self.template_name, {
            'expense': res.json(), 
            'categories': api_call(request, '/api/categories/').json()
        })
    
    def post(self, request, pk):
        if 'delete' in request.POST:
            res = api_call(request, f'/api/expenses/{pk}/', 'delete')
            if res.status_code == 204:
                return redirect('expenses')
            else:
                raise Http404
        else:  
            res = api_call(request, f'/api/expenses/{pk}/', 'put', data={
                'amount': request.POST['amount'],
                'category': request.POST['category'],
                'date': request.POST['date'],
                'description': request.POST['description'],
            })
            if res.status_code == 200:
                return redirect('expense_detail', pk=pk)
            return render(request, self.template_name, {
                'expense': api_call(request, f'/api/expenses/{pk}/').json(),
                'categories': api_call(request, '/api/categories/').json(),
                'errors': res.json(),
        })

class IncomeListCreateView(LoginRequiredMixin, View):
    template_name = 'incomes.html'
    
    def get(self, request):
        res = api_call(request, '/api/incomes')
        if res.status_code == 404:
            raise Http404
        return render(request, self.template_name, {'incomes': res.json()})

    def post(self, request):
        res = api_call(request, '/api/incomes/', 'post', data={
            'amount': request.POST['amount'],
            'date': request.POST['date'],
        })
        if res.status_code == 201:
            return redirect('incomes')
        return render(request, self.template_name, {
            'incomes': api_call(request, '/api/incomes/').json(),
            'errors': res.json(),
        })

class CategoryListCreateView(LoginRequiredMixin, View):
    template_name = 'categories.html'
    def get(self, request):
        res = api_call(request, '/api/categories')
        if res.status_code == 404:
            raise Http404
        return render(request, self.template_name, {'categories': res.json()})

    def post(self, request):
        res = api_call(request, '/api/categories/', 'post', data={
            'name': request.POST['name'],
        })
        if res.status_code == 201:
            return redirect('categories')
        return render(request, self.template_name, {
            'categories': api_call(request, '/api/categories/').json(),
            'errors': res.json(),
        })
class AnalyticsView(LoginRequiredMixin, View):
    template_name = 'analytics.html'

    def get(self, request):
        return render(request, self.template_name, self.context(request))

    def post(self, request):
        context = self.context(
            request,
            selected_month=request.POST['month'],
            selected_category=int(request.POST['category']),
        )
        return render(request, self.template_name, context)

    def context(self, request, selected_month=None, selected_category=None):
        expenses_res = api_call(request, '/api/expenses/', params={'page_size': 1000})
        incomes_res = api_call(request, '/api/incomes/')
        categories_res = api_call(request, '/api/categories/')
        if expenses_res.status_code == 404 or incomes_res.status_code == 404 or categories_res.status_code == 404:
            raise Http404
    
        expenses = expenses_res.json()['results']
        incomes = incomes_res.json()
        categories = categories_res.json()
        total_expenses = sum(float(e['amount']) for e in expenses)
        total_income = sum(float(i['amount']) for i in incomes)
    
        if selected_month is None:
            selected_month = localdate().strftime('%Y-%m')
        if selected_category is None:
            selected_category = categories[0]['id'] if categories else None
    
        filtered_expenses = [
            e for e in expenses
            if e['date'].startswith(selected_month) and e['category'] == selected_category
        ]
        return {
            'expenses': filtered_expenses,
            'categories': categories,
            'selected_month': selected_month,
            'selected_category': selected_category,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'balance': total_income - total_expenses,
        }

class CategoryListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CategorySerializer
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user)

class ExpensePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000

class ExpenseListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ExpenseSerializer
    pagination_class = ExpensePagination
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