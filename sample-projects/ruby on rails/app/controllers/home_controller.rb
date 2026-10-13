class HomeController < ApplicationController
  def index
    render json: {
      message: "Hello from the multi-stage Rails sample project",
      environment: Rails.env
    }
  end
end
