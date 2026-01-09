from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AIRecommendationAnonThrottle(AnonRateThrottle):
    """
    Rate limiting for anonymous users accessing AI recommendation endpoint
    Limit: 10 requests per hour
    """
    rate = '10/hour'  # 10 requests per hour
    scope = 'ai_recommend_anon'


class AIRecommendationUserThrottle(UserRateThrottle):
    """
    Rate limiting for authenticated users accessing AI recommendation endpoint
    Limit: 30 requests per hour (more generous for authenticated users)
    """
    rate = '30/hour'  # 30 requests per hour
    scope = 'ai_recommend_user'
