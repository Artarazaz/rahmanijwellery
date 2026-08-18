from rest_framework import serializers

from .models import GoldPrice


class GoldPriceSerializer(serializers.ModelSerializer):

    class Meta:
        model = GoldPrice
        fields = "__all__"