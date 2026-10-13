Rails.application.routes.draw do
  root "home#index"
  get "/health", to: "health#show"
end
