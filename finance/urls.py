from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from finance import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('create_account/', views.create_account, name='create_account'),
    path('logout/', views.logout_view, name='logout'),
    path('expenses/', views.ExpenseListCreateView.as_view(), name='expenses'),
    path('incomes/', views.ExpenseListCreateView.as_view(), name='incomes'),
    path('categories/', views.ExpenseListCreateView.as_view(), name='categories'),
    path('analytics/', views.ExpenseListCreateView.as_view(), name='analytics'),
    path('api/categories/', views.CategoryListCreateAPIView.as_view()),  
    path('api/expenses/', views.ExpenseListCreateAPIView.as_view()),  
    path('api/expenses/<int:pk>/', views.ExpenseDetailAPIView.as_view()),  
    path('api/incomes/', views.IncomeListCreateAPIView.as_view()),  
]

urlpatterns += [
    path("api-auth/", include("rest_framework.urls")),
    path("api-token-auth/", obtain_auth_token, name="api_token_auth"),
]