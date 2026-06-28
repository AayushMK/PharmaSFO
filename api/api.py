from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.authentication import JWTAuth
from ninja import Router

api = NinjaExtraAPI(title="PharmaSFO API", version="1.0.0")
api.register_controllers(NinjaJWTDefaultController)

doctor_router = Router(tags=["Doctors"])


@doctor_router.get("/", auth=JWTAuth())
def list_doctors(request):
    from doctors.models import Doctor
    return list(Doctor.objects.values("id", "name", "nmc_number", "area"))


api.add_router("/doctors", doctor_router)
