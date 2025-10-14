from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Group, Alarm, AlarmLog
from .serializers import (
    UserSerializer, UserProfileSerializer, GroupSerializer, 
    GroupCreateSerializer, AlarmSerializer, AlarmLogSerializer
)

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')
        
        if not phone_number or not password:
            return Response(
                {'error': 'Phone number and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(phone_number=phone_number, password=password)
        
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token)
                }
            })
        
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Update current user profile"""
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    
    def get_serializer_class(self):
        if self.action == "create":
            return GroupCreateSerializer
        return GroupSerializer
    
    def get_queryset(self):
        """Return groups that user is a member of, except for join action"""
        if self.action == "join":
            return Group.objects.all()
        return self.queryset.filter(members=self.request.user)
    
    def perform_create(self, serializer):
        """Create group and add creator as first member"""
        group = serializer.save(created_by=self.request.user)
        group.members.add(self.request.user)
        
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a group"""
        group = self.get_object()
        if request.user in group.members.all():
            return Response(
                {'error': 'Already a member of this group'},
                status = status.HTTP_400_BAD_REQUEST
            )
        
        group.members.add(request.user)
        serializer = self.get_serializer(group)
        return Response({
            'message': 'Successfully joined group',
            'group': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a group"""
        group = self.get_object()
        if request.user not in group.members.all():
            return Response(
                {'error': 'Not a member of this group'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        group.members.remove(request.user)
        return Response(
            {'message': 'Successfully left the group'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """List all members of a group"""
        group = self.get_object()
        serializer = UserProfileSerializer(group.members.all(), many=True)
        return Response(serializer.data)

class AlarmViewSet(viewsets.ModelViewSet):
    queryset = Alarm.objects.all()
    serializer_class = AlarmSerializer
    
    def get_queryset(self):
        """Return alarms for groups the user is a member of"""
        return self.queryset.filter(group__members=self.request.user)
    
    def perform_create(self, serializer):
        """Set creator when creating alarm"""
        serializer.save(created_by=self.request.user)
        
    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """Toggle the alarm's active status"""
        alarm = self.get_object()
        alarm.is_active = not alarm.is_active
        alarm.save()
        return Response({
            'is_active': alarm.is_active,
            'message': f"Alarm {"activated" if alarm.is_active else "deactivated"}"
        })
        
    @action(detail=True, methods=['get'])
    def my_alarms(self, request):
        """Get alarms created by current user"""
        alarms = self.queryset.filter(created_by=request.user)
        serializer = self.get_serializer(alarms, many=True)
        return Response(serializer.data)
        
class AlarmLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AlarmLog.objects.all()
    serializer_class = AlarmLogSerializer
    
    def get_queryset(self):
        """Return alarm logs for user's alarms"""
        return self.queryset.filter(user=self.request.user).order_by('-triggered_at')
