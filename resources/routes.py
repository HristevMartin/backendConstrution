from resources.auth import (
    Register,
    Login,
    Test,
    Logout,
    ForgotPassword,
    ResetPassword,
    GetSession,
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
from resources.ClientProjects import ClientProjects, GetClientProject, EditClientProject, GetAllClientProjects, DeleteClientProjectId
from resources.TraderProjects import SaveTraderProject, GetTraderProject
from resources.Payments import PayWithStripe, CheckPaymentStatus
from resources.ChatComponent import ChatComponent, CreateChat, GetAllChats, GetConversationById, ChatSummary, MarkConversationRead
from resources.track_visits import SimplePageTrackingResource, GetPageVisits
from resources.JobApplicationCounter import JobApplicationCounterResource
from resources.User import GetUserData, PostUserRadiusKm
from resources.ai_helper import AIHelper, AITraderHelper
from resources.ClientCompletedJobs import GetClientCompletedJobs, GetAllClientStatusProjects
from resources.trader_rating import TraderRating, PastJobs, GetTraderRating
from resources.verified_trader import VerifiedTrader
from resources.verify_homeowner import CheckVerifiedHomeowner
from resources.chat_agent import UIchatAgent
from resources.notify_trader_email import NotifyTraderByEmailFromChat
from resources.ai_helper import AIGeneralChat
from resources.health_check import HealthCheck, SecondHealthCheck, ThirdHealthCheck
from resources.Payments import StripeWebhookTest
from resources.client_projects_utils import CheckIfAnyJobIsPaid
from resources.HomeOwnerVerification import HomeOwnerVerification
from resources.auth import GoogleAuth
from resources.job_applicants import GetApplicantsPerJob


routes = [
    (Register, "/travel/register"),
    (Login, "/travel/login"),
    (GoogleAuth, "/travel/auth/google"),
    (Logout, "/travel/logout"),
    (ForgotPassword, "/travel/forgot-password"),
    (ClientProjects, "/travel/save-client-project"),
    (GetClientProject, "/travel/get-client-project/<project_id>"),
    (EditClientProject, "/travel/edit-client-project/<project_id>"),
    (DeleteClientProjectId, "/travel/delete-client-project/<project_id>"),
    (SaveTraderProject, "/travel/save-trader-project"),
    (GetTraderProject, "/travel/get-trader-project/<user_id>"),
    (GetUserRole, "/travel/get-user-role"),
    (GetUserData, "/travel/get-user-data"),
    (PostUserRadiusKm, "/travel/post-user-radius-km"),
    (GetAllClientProjects, "/travel/get-all-client-projects"),
    (PayWithStripe, "/api/payments/create-intent"),
    (CheckPaymentStatus, "/api/payments/check-payment-status/<user_id>/<job_id>"),
    (ChatComponent, "/travel/chat-component/<conversation_id>"),
    (CreateChat, "/travel/chat-component/create-chat"),
    (GetAllChats, "/travel/chat-component/get-all-chats"),
    (GetConversationById, "/travel/chat-component/get-conversation-by-id/<job_id>"),
    (ChatSummary, "/travel/chat-component/chat-summary"),
    (MarkConversationRead, "/travel/chat-component/mark-as-read/<conversation_id>"),
    (ResetPassword, "/travel/reset-password"),
    (GetSession, "/travel/auth/session"),
    (SimplePageTrackingResource, "/travel/track-visit"),
    (GetPageVisits, "/travel/page-visits"),
    (JobApplicationCounterResource, "/travel/job-application-counter/<job_id>"),
    (AIHelper, "/travel/ai-helper"),
    (AITraderHelper, "/travel/trader-helper"),
    (GetClientCompletedJobs, "/travel/get-client-completed-jobs/<job_id>"),
    (GetAllClientStatusProjects, "/travel/get-all-client-status-projects"),
    (TraderRating, "/travel/get-trader-completed-job"),
    (PastJobs, "/travel/past-jobs"),
    (GetTraderRating, "/travel/get-trader-rating"),
    (VerifiedTrader, "/travel/check-verified-trader/<user_id>"),
    (CheckVerifiedHomeowner, "/travel/check-verified-homeowner/<job_id>"),
    (UIchatAgent, "/travel/ai/homeowner-chat"),
    (NotifyTraderByEmailFromChat, "/travel/ai/notify-trader-by-email-from-chat"),
    (AIGeneralChat, "/travel/ai/general-chat"),
    (HealthCheck, "/travel/health-check"),
    (SecondHealthCheck, "/travel/second-health-check"),
    (ThirdHealthCheck, "/travel/third-health-check"),
    (StripeWebhookTest, "/api/payments/webhook-test"),
    (CheckIfAnyJobIsPaid, "/api/payments/check-if-any-job-is-paid/<job_id>"),
    (HomeOwnerVerification, "/api/homeowner/verify/user"),
    (GetApplicantsPerJob, "/api/job-applicants/<job_id>")
]
