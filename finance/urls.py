from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from finance import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('create_account/', views.create_account, name='create_account'),
    path('logout/', views.logout_view, name='logout'),
    path('categories/', views.CategoryListCreateView.as_view()),  
    path('expenses/', views.ExpenseListCreateView.as_view()),  
    path('expenses/<int:pk>/', views.ExpenseDetailView.as_view()),  
    path('incomes/', views.IncomeListCreateView.as_view()),  
]

urlpatterns += [
    path("api-auth/", include("rest_framework.urls")),
    path("api-token-auth/", obtain_auth_token, name="api_token_auth"),
]