from rest_framework import serializers
from .models import Competition, Task, Participation, Solution, SolutionGradeEvent
from .task_visibility import task_schedule_gate, user_can_view_task_content


class CompetitionSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Competition
        fields = (
            'id', 'title', 'description', 'audience', 'level', 'status',
            'start_time', 'end_time', 'min_age', 'max_age', 'max_participants',
            'created_at', 'updated_at',
            'created_by', 'created_by_username',
        )
        read_only_fields = ('created_at', 'updated_at', 'created_by')


class TaskSerializer(serializers.ModelSerializer):
    schedule_gate = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Task
        fields = (
            'id', 'competition', 'subject', 'task_type',
            'title', 'description', 'order',
            'max_score', 'expected_output',
            'opens_at', 'closes_at', 'schedule_gate',
            'created_at', 'updated_at',
        )
        read_only_fields = ('competition', 'created_at', 'updated_at', 'schedule_gate')

    def get_schedule_gate(self, obj):
        return task_schedule_gate(obj)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get('hide_expected_output'):
            data.pop('expected_output', None)
        request = self.context.get('request')
        if request is not None and not user_can_view_task_content(request.user, instance):
            data['description'] = ''
        return data


class ParticipationSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    competition_title = serializers.CharField(source='competition.title', read_only=True)

    class Meta:
        model = Participation
        fields = ('id', 'user', 'user_username', 'competition', 'competition_title', 'registered_at')
        read_only_fields = ('registered_at',)


class SolutionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)

    class Meta:
        model = Solution
        fields = (
            'id', 'user', 'user_username', 'task', 'task_title',
            'content', 'submitted_at', 'status', 'score', 'comment',
        )
        read_only_fields = ('task', 'content', 'submitted_at', 'status', 'score', 'user')

    def get_fields(self):
        fields = super().get_fields()
        if not self.context.get('can_grade'):
            for f in ('status', 'score', 'comment'):
                if f in fields:
                    fields[f].read_only = True
        return fields


class SolutionGradeEventSerializer(serializers.ModelSerializer):
    graded_by_username = serializers.CharField(source='graded_by.username', read_only=True)

    class Meta:
        model = SolutionGradeEvent
        fields = (
            'id',
            'solution',
            'graded_by',
            'graded_by_username',
            'from_status',
            'to_status',
            'from_score',
            'to_score',
            'from_comment',
            'to_comment',
            'note',
            'created_at',
        )
        read_only_fields = fields


class SolutionSubmitSerializer(serializers.ModelSerializer):
    """Только отправка решения (поле content)."""
    class Meta:
        model = Solution
        fields = ('content',)


class ResultEntrySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    total_score = serializers.IntegerField()
