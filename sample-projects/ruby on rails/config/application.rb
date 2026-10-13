require_relative "boot"

require "rails/all"

Bundler.require(*Rails.groups)

module RailsMultiStageSample
  class Application < Rails::Application
    config.load_defaults 7.1
    config.autoload_lib(ignore: %w[assets tasks])
    config.active_job.queue_adapter = :async
    config.time_zone = "UTC"
    config.eager_load = true
  end
end
