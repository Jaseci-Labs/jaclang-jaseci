"""User Models."""

from typing import Any, Mapping, Type, Union, cast

from passlib.hash import pbkdf2_sha512

from pydantic import BaseModel, EmailStr, create_model
from pydantic.fields import FieldInfo

from ..collections.user import UserCollection

NULL_BYTES = bytes()


class UserCommon(BaseModel):
    """User Common Functionalities."""

    password: bytes

    def serialize(self) -> dict:
        """Return BaseModel.model_dump excluding the password field."""
        return self.model_dump(exclude={"password"})

    def obfuscate(self) -> dict:
        """Return BaseModel.model_dump where the password is hashed."""
        data = self.serialize()
        if isinstance(self.password, str):
            data["password"] = pbkdf2_sha512.hash(self.password).encode()
        return data


class User(UserCommon):
    """User Base Model."""

    id: str
    email: EmailStr
    password: bytes
    root_id: str
    is_activated: bool = False

    class Collection(UserCollection["User"]):
        """UserCollection Integration."""

        @classmethod
        def __document__(cls, doc: Union[Mapping[str, Any]]) -> "User":
            """
            Return parsed User from document.

            This the default User parser after getting a single document.
            You may override this to specify how/which class it will be casted/based.
            """
            doc = cast(dict, doc)
            return User.model()(
                id=str(doc.pop("_id")),
                password=cast(bytes, doc.pop("password")) or NULL_BYTES,
                root_id=str(doc.pop("root_id")),
                **doc,
            )

    @staticmethod
    def model() -> Type["User"]:
        """Retrieve the preferred User Model from subclasses else this class."""
        if subs := User.__subclasses__():
            return subs[-1]
        return User

    @staticmethod
    def register_type() -> type:
        """Generate User Registration Model based on preferred User Model for FastAPI endpoint validation."""
        user_model: dict[str, Any] = {}
        fields: dict[str, FieldInfo] = User.model().model_fields
        for key, val in fields.items():
            if callable(val.default_factory):
                user_model[key] = (val.annotation, val.default_factory())
            else:
                user_model[key] = (val.annotation, ...)

        user_model["password"] = (str, ...)
        user_model.pop("id", None)
        user_model.pop("root_id", None)
        user_model.pop("is_activated", None)

        return create_model("UserRegister", __base__=UserCommon, **user_model)

    @staticmethod
    def send_verification_code(code: str, email: str) -> None:
        """Send verification code."""
        pass