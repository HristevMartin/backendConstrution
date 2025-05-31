from resources.auth import (
    Register,
    Login,
    Test,
    Logout,
)

from resources.TraderForm import TraderForm
from resources.UserTrack import UserTrack
from resources.TraderProject import SaveProject
from resources.User import GetUser
from resources.GetProjectServices import GetProjectServices, GetSpecificServices
from resources.StaticFiles import ServeUploadedFile

routes = [
    (Register, "/travel/register"),
    (Login, "/travel/login"),
    (Logout, "/travel/logout"),
    (Test, "/travel/some"),
    (TraderForm, "/travel/save-profile"),
    (UserTrack, "/travel/save-user-track"),
    (SaveProject, "/travel/save-project"),
    (GetUser, "/travel/get-user/<user_id>"),
    (GetProjectServices, "/travel/get-project-services"),
    (GetSpecificServices, "/travel/get-specific-services/<trade>"),
    (ServeUploadedFile, "/uploads/<folder>/<user_id>/<filename>")
]
