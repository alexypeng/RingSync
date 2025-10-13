from rest_framework import serializers
from .models import User, Group, Alarm, AlarmLog

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'name', 'password', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            name=validated_data['name'],
            password=validated_data['password']
        )
        
        return user
    
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'phone_number', 'created_at', 'updated_at']

class GroupSerializer(serializers.ModelSerializer):
    created_by = UserProfileSerializer(read_only=True)
    members = UserProfileSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'created_by', 'members', 'member_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
        
    def get_member_count(self, obj):
        return obj.members.count()
    
class GroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']
        read_only_fields = ['id']
        
class AlarmSerializer(serializers.ModelSerializer):
    created_by = UserProfileSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    
    class Meta:
        model = Alarm
        fields = ['id', 'group', 'name', 'time', 'days_of_week', 'is_active', 
                  'created_by', 'group_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
        
    def validate(self, data):
        """Auto-set days_of_week to next occurrence if not provided"""
        from django.utils import timezone
        
        if 'days_of_week' not in data or not data['days_of_week']:
            alarm_time = data.get('time')
            if alarm_time:
                now = timezone.now()
                current_time = now.time()
                current_day = now.weekday()
            
                if alarm_time > current_time:
                    data['days_of_week'] = str(current_day)
                else:
                    tomorrow = (current_day + 1) % 7
                    data['days_of_week'] = str(tomorrow)
        
        return data

    def validate_days_of_week(self, value):
        """Validate days_of_week format (comma-separated 0-6)"""
        if not value:
            return value
        
        days = value.split(',')
        for day in days:
            try:
                day_int = int(day.strip())
                if day_int < 0 or day_int > 6:
                    raise serializers.ValidationError("Days must be between 0 (Monday) and 6 (Sunday)")
            except ValueError:
                raise serializers.ValidationError("Days must be numeric values")
        
        return value

class AlarmLogSerializer(serializers.ModelSerializer):
    alarm_name = serializers.CharField(source='alarm.name', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = AlarmLog
        fields = ['id', 'alarm', 'alarm_name', 'user', 'user_name', 
                  'triggered_at', 'call_sid', 'call_status']
        read_only_fields = ['id', 'triggered_at']
