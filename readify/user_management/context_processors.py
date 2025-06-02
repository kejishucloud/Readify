from .views import get_user_stats


def user_stats_context(request):
    """全局用户统计数据上下文处理器"""
    if request.user.is_authenticated:
        return {
            'user_stats': get_user_stats(request.user)
        }
    return {
        'user_stats': {
            'total_books': 0,
            'categories_count': 0,
            'total_views': 0,
            'notes_count': 0,
            'upload_errors': 0,
        }
    } 