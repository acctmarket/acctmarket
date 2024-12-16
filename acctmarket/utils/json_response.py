from django.http import JsonResponse


class JsonResponseMixin:
    def render_to_json_response(self, context, **response_kwargs):
        """
        Render the given context dictionary into a JSON response object.

        Args:
            context (dict): The context dictionary to be rendered into JSON.
            **response_kwargs: Additional keyword arguments to be passed to the
                `JsonResponse` constructor.

        Returns:
            JsonResponse: The JSON response object.
        """
        return JsonResponse(context, **response_kwargs)
