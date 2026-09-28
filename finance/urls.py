from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from finance import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('create_account/', views.CreateAccountView.as_view(), name='create_account'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('expenses/', views.ExpenseListCreateView.as_view(), name='expenses'),
    path('expenses/<int:pk>/', views.ExpenseDetailView.as_view(), name='expense_detail'),
    path('incomes/', views.IncomeListCreateView.as_view(), name='incomes'),
    path('categories/', views.CategoryListCreateView.as_view(), name='categories'),
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    path('api/categories/', views.CategoryListCreateAPIView.as_view()),  
    path('api/expenses/', views.ExpenseListCreateAPIView.as_view()),  
    path('api/expenses/<int:pk>/', views.ExpenseDetailAPIView.as_view()),  
    path('api/incomes/', views.IncomeListCreateAPIView.as_view()),  
]

urlpatterns += [
    path("api-auth/", include("rest_framework.urls")),
    path("api-token-auth/", obtain_auth_token, name="api_token_auth"),
]