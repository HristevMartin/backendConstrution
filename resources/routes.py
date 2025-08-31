from resources.auth import (
    Register,
    Login,
    Test,
    Logout,
)

from resources.TraderForm import TraderForm
from resources.UserTrack import UserTrack
from resources.TraderProject import SaveProject, UpdateProject
from resources.User import GetUser, SaveUserRole, GetUserRole
from resources.GetProjectServices import GetProjectServices, GetSpecificServices
from resources.StaticFiles import ServeUploadedFile
from resources.TraderProject import GetProjectByID
from resources.TraderForm import GetProfileByID
from resources.TraderProject import GetAllProfiles
from resources.CommentResource import SaveComment, GetCommentsByProjectId, DeleteComment, UpdateComment
from resources.ClientProjects import ClientProjects, GetClientProject, EditClientProject, GetAllClientProjects
from resources.TraderProjects import SaveTraderProject, GetTraderProject


routes = [
    (Register, "/travel/register"),
    (Login, "/travel/login"),
    (Logout, "/travel/logout"),
    # (Test, "/travel/some"),
    # (TraderForm, "/travel/save-profile"),
    # (GetAllProfiles, "/travel/get-all-profiles"),
    # (UserTrack, "/travel/save-user-track"),
    # (SaveProject, "/travel/save-project"),
    # (UpdateProject, "/travel/update-project/<project_id>"),
    # (GetProjectByID, "/travel/get-project-by-id/<project_id>"),
    # (GetProfileByID, "/travel/get-profile-by-id/<profile_id>"),
    # (GetUser, "/travel/get-user/<user_id>"),
    # (GetProjectServices, "/travel/get-project-services"),
    # (GetSpecificServices, "/travel/get-specific-services/<trade>"),
    # (SaveComment, "/travel/save-comment"),
    # (GetCommentsByProjectId, "/travel/get-comments/<project_id>"),
    # (DeleteComment, "/travel/delete-comment/<comment_id>"),
    # (UpdateComment, "/travel/update-comment/<comment_id>"),
    # (ServeUploadedFile, "/uploads/<folder>/<user_id>/<filename>"),
    # (SaveUserRole, "/travel/role-selected"),
    # ##UI revamp endpoints
    (ClientProjects, "/travel/save-client-project"),
    (GetClientProject, "/travel/get-client-project/<project_id>"),
    (EditClientProject, "/travel/edit-client-project/<project_id>"),
    (SaveTraderProject, "/travel/save-trader-project"),
    (GetTraderProject, "/travel/get-trader-project/<user_id>"),
    (GetUserRole, "/travel/get-user-role"),
    (GetAllClientProjects, "/travel/get-all-client-projects"),
]
