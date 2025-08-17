"""Request validators using Pydantic schemas"""

from functools import wraps
from typing import Callable, Type

from bulletin_board.api.schemas import BaseModel
from flask import jsonify, request
from pydantic import ValidationError


def validate_json(schema: Type[BaseModel]):
    """Decorator to validate JSON request body against a Pydantic schema"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Get JSON data from request
                json_data = request.get_json()
                if json_data is None:
                    return jsonify({"error": "No JSON data provided"}), 400

                # Validate against schema
                validated_data = schema(**json_data)

                # Add validated data to kwargs
                kwargs["validated_data"] = validated_data

                return f(*args, **kwargs)

            except ValidationError as e:
                errors = []
                for error in e.errors():
                    field = " -> ".join(str(x) for x in error["loc"])
                    errors.append({"field": field, "message": error["msg"], "type": error["type"]})

                return jsonify({"error": "Validation failed", "details": errors}), 400
            except Exception as e:
                return jsonify({"error": "Invalid request", "details": str(e)}), 400

        return wrapper

    return decorator


def validate_query_params(schema: Type[BaseModel]):
    """Decorator to validate query parameters against a Pydantic schema"""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Get query parameters
                query_params = request.args.to_dict()

                # Convert to appropriate types (query params are always strings)
                for key, value in query_params.items():
                    if value.isdigit():
                        query_params[key] = int(value)
                    elif value.lower() in ("true", "false"):
                        query_params[key] = value.lower() == "true"

                # Validate against schema
                validated_params = schema(**query_params)

                # Add validated params to kwargs
                kwargs["query_params"] = validated_params

                return f(*args, **kwargs)

            except ValidationError as e:
                errors = []
                for error in e.errors():
                    field = " -> ".join(str(x) for x in error["loc"])
                    errors.append({"field": field, "message": error["msg"], "type": error["type"]})

                return (
                    jsonify({"error": "Invalid query parameters", "details": errors}),
                    400,
                )
            except Exception as e:
                return jsonify({"error": "Invalid request", "details": str(e)}), 400

        return wrapper

    return decorator
