from django.views import View
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from finance.models import Category, Expense, Income
from finance.serializers import CategorySerializer, ExpenseSerializer, IncomeSerializer
from rest_framework import generics, permissions
from .permissions import IsOwner
from django.contrib.auth.mixins import LoginRequiredMixin
import requests
from django.http import Http404
from django.utils.timezone import localdate

def api_call(request, path, method='get', **kwargs):
    #Call our own REST API as the logged-in user by authenticating with their token
    token = Token.objects.get_or_create(user=request.user)[0].key
    return requests.request(
        method,
        request.build_absolute_uri(path),
        headers={'Authorization': f'Token {token}'},
        **kwargs,
    )

class ExpensePagination(PageNumberPagination):
    # 10 per page by default; clients can ask for more with ?page_size=N, up to 1000
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000

class HomeView(LoginRequiredMixin, View):
    # LoginRequiredMixin sends anonymous users to LOGIN_URL (/login/)
    template_name = 'home.html'
    def get(self, request):
        return render(request, self.template_name)

class LogoutView(View):
    # Ends the session and returns to the login page, so it needs no template
    def get(self, request):
        logout(request)
        return redirect('login')

class CreateAccountView(View):
    template_name = 'create_account.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Validate by hand; on failure re-render the form with a message and 400 (bad input)
        error = None
        if not username or not password:
            error = "Username and password are required."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif User.objects.filter(username=username).exists():
            error = "Username already taken."
        if error:
            return render(request, self.template_name, {'error': error, 'username': username}, status=400)

        user = User.objects.create_user(username=username, password=password)  # hashes the password
        # Every account gets an API token so it can also authenticate with the token header
        Token.objects.get_or_create(user=user)
        # Log in with a session too, so the browser pages work straight away
        login(request, user)
        return redirect('home')

class LoginView(View):
    template_name = 'login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        # authenticate() returns None for wrong credentials; 401 = not authenticated
        if user is None:
            return render(request, self.template_name, {
                'error': "Invalid username or password.",
                'username': username,
            }, status=401)
        # Accounts created before tokens existed (e.g. an admin) get theirs on first login
        Token.objects.get_or_create(user=user)
        login(request, user)
        return redirect('home')

class ExpenseListCreateView(LoginRequiredMixin, View):
    #Lists the user's expenses and adds new ones
    #Reads and writes through endpoints instead of touching the db
    template_name = 'expenses.html'

    def get(self, request):
        return render(request, self.template_name, self.context(request))

    def post(self, request):
        # Forward the form to the API, which validates and saves it (201 = created)
        res = api_call(request, '/api/expenses/', 'post', data={
            'amount': request.POST.get('amount'),
            'category': request.POST.get('category'),
            'date': request.POST.get('date'),
            'description': request.POST.get('description'),
        })  
        if res.status_code == 201:
            # Redirect after POST so refreshing the page doesn't resubmit the form
            return redirect('expenses')
        # Validation failed: redisplay the page with the API's error messages
        return render(request, self.template_name, {**self.context(request), 'errors': res.json()}, status=400)

    def context(self, request):
        # A non-numeric page is a 404, the same as the API returns for an out-of-range page
        try:
            current_page = int(request.GET.get('page', 1))
        except ValueError:
            raise Http404
        expenses_res =  api_call(request, '/api/expenses/', params={'page': current_page})
        categories_res = api_call(request, '/api/categories/')
        if expenses_res.status_code == 404 or categories_res.status_code == 404:
            raise Http404
        expenses_data = expenses_res.json()
        return {
            'expenses': expenses_data['results'],
            'categories': categories_res.json(),
            'current_page': current_page,
            # DRF pagination gives URLs in next/previous, or None on the last/first page
            'has_next': expenses_data['next'] is not None,
            'has_previous': expenses_data['previous'] is not None,
        }

class ExpenseDetailView(LoginRequiredMixin, View):
    template_name = "expense_detail.html"

    def get(self, request, pk):
        # The API returns 404 both for a missing expense and for another user's expense
        res = api_call(request, f'/api/expenses/{pk}/')
        if res.status_code == 404:
            raise Http404
        return render(request, self.template_name, {
            'expense': res.json(), 
            'categories': api_call(request, '/api/categories/').json()
        })
    
    def post(self, request, pk):
        # The Delete button submits with name="delete"; otherwise this is the edit form
        if 'delete' in request.POST:
            res = api_call(request, f'/api/expenses/{pk}/', 'delete')
            if res.status_code == 204:
                return redirect('expenses')
            else:
                raise Http404
        else:  
            # The form sends every field, so this is a full update (PUT)
            res = api_call(request, f'/api/expenses/{pk}/', 'put', data={
                'amount': request.POST.get('amount'),
                'category': request.POST.get('category'),
                'date': request.POST.get('date'),
                'description': request.POST.get('description'),
            })
            if res.status_code == 200:
                return redirect('expense_detail', pk=pk)
            return render(request, self.template_name, {
                'expense': api_call(request, f'/api/expenses/{pk}/').json(),
                'categories': api_call(request, '/api/categories/').json(),
                'errors': res.json(),
            }, status=400)

class IncomeListCreateView(LoginRequiredMixin, View):
    # Lists the user's income and adds new entries, through /api/incomes/
    template_name = 'incomes.html'
    
    def get(self, request):
        res = api_call(request, '/api/incomes/')
        if res.status_code == 404:
            raise Http404
        return render(request, self.template_name, {'incomes': res.json()})

    def post(self, request):
        res = api_call(request, '/api/incomes/', 'post', data={
            'amount': request.POST.get('amount'),
            'date': request.POST.get('date'),
        })
        if res.status_code == 201:
            return redirect('incomes')
        return render(request, self.template_name, {
            'incomes': api_call(request, '/api/incomes/').json(),
            'errors': res.json(),
        }, status=400)

class CategoryListCreateView(LoginRequiredMixin, View):
    # Lists the user's categories and adds new ones, through /api/categories/
    template_name = 'categories.html'
    def get(self, request):
        res = api_call(request, '/api/categories/')
        if res.status_code == 404:
            raise Http404
        return render(request, self.template_name, {'categories': res.json()})

    def post(self, request):
        res = api_call(request, '/api/categories/', 'post', data={
            'name': request.POST.get('name'),
        })
        if res.status_code == 201:
            return redirect('categories')
        return render(request, self.template_name, {
            'categories': api_call(request, '/api/categories/').json(),
            'errors': res.json(),
        }, status=400)
    
class AnalyticsView(LoginRequiredMixin, View):
    # Monthly summary: overall totals plus the expenses for one month and category
    template_name = 'analytics.html'

    def get(self, request):
        return render(request, self.template_name, self.context(request))

    def post(self, request):
        context = self.context(
            request,
            selected_month=request.POST.get('month'),
            selected_category=int(request.POST.get('category')),
        )
        return render(request, self.template_name, context)

    def context(self, request, selected_month=None, selected_category=None):
        # page_size=1000 is the API's maximum, so all expenses come back in one request
        expenses_res = api_call(request, '/api/expenses/', params={'page_size': 1000})
        incomes_res = api_call(request, '/api/incomes/')
        categories_res = api_call(request, '/api/categories/')
        if expenses_res.status_code == 404 or incomes_res.status_code == 404 or categories_res.status_code == 404:
            raise Http404
    
        expenses = expenses_res.json()['results']
        incomes = incomes_res.json()
        categories = categories_res.json()
        # Totals cover everything; only the table is filtered by month and category
        total_expenses = sum(float(e['amount']) for e in expenses)
        total_income = sum(float(i['amount']) for i in incomes)
    
        # Default to the current month and the first category
        if selected_month is None:
            selected_month = localdate().strftime('%Y-%m')
        if selected_category is None:
            selected_category = categories[0]['id'] if categories else None
    
        # Dates look like "2026-09-28", so startswith("2026-09") matches a whole month
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
    # The JSON API: token-authenticated (see REST_FRAMEWORK in settings) and scoped to the user
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CategorySerializer
    # The owner comes from the authenticated user, never from the request body
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user)

class ExpenseListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ExpenseSerializer
    pagination_class = ExpensePagination
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    def get_queryset(self):
        return Expense.objects.filter(owner=self.request.user)

class ExpenseDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    # The queryset already hides other users' expenses (404); IsOwner is a second, object-level check
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