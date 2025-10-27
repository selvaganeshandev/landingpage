from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from .models import Organisation, Account, TeamInvitation, UserPermission
from .serializers import (
    OrganisationSerializer, AccountSerializer, OrganisationDetailSerializer,
    AccountCreateSerializer, AccountUpdateSerializer,
    TeamInvitationSerializer, TeamInvitationCreateSerializer,
    UserPermissionSerializer, UserPermissionCreateSerializer
)


# Organisation Views
@api_view(['GET', 'POST'])
def organisation_list(request):
    """List all organisations or create a new one"""
    if request.method == 'GET':
        organisations = Organisation.objects.all()
        serializer = OrganisationSerializer(organisations, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = OrganisationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def organisation_detail(request, pk):
    """Retrieve, update or delete an organisation"""
    organisation = get_object_or_404(Organisation, pk=pk)
    
    if request.method == 'GET':
        serializer = OrganisationDetailSerializer(organisation)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = OrganisationSerializer(organisation, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        organisation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def organisation_accounts(request, pk):
    """Get all accounts for an organisation"""
    organisation = get_object_or_404(Organisation, pk=pk)
    accounts = organisation.accounts.all()
    serializer = AccountSerializer(accounts, many=True)
    return Response(serializer.data)    


# Account Views
@api_view(['GET', 'POST'])
def account_list(request):
    """List all accounts or create a new one"""
    if request.method == 'GET':
        accounts = Account.objects.all()
        serializer = AccountSerializer(accounts, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = AccountCreateSerializer(data=request.data)
        if serializer.is_valid():
            account = serializer.save()
            return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def account_detail(request, pk):
    """Retrieve, update or delete an account"""
    account = get_object_or_404(Account, pk=pk)
    
    if request.method == 'GET':
        serializer = AccountSerializer(account)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = AccountUpdateSerializer(account, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(AccountSerializer(account).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        account.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Authentication Views
@api_view(['POST'])
def login(request):
    """Login endpoint for account authentication"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {'error': 'Email and password are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Authenticate user
    user = authenticate(username=email, password=password)
    if user is not None:
        token, created = Token.objects.get_or_create(user=user)
        serializer = AccountSerializer(user)
        return Response({
            'token': token.key,
            'user': serializer.data
        })
    else:
        return Response(
            {'error': 'Invalid credentials'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
def logout(request):
    """Logout endpoint"""
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'})
    except:
        return Response(
            {'error': 'Invalid token'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
def account_profile(request):
    """Get current user profile"""
    if request.user.is_authenticated:
        serializer = AccountSerializer(request.user)
        return Response(serializer.data)
    else:
        return Response(
            {'error': 'Authentication required'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['PUT'])
def account_profile_update(request):
    """Update current user profile"""
    if request.user.is_authenticated:
        serializer = AccountUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(AccountSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response(
            {'error': 'Authentication required'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )