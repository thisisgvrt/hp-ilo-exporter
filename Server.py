import logging
import logging.config

import yaml
from hpilo import Ilo
from prometheus_client import Gauge
from prometheus_client.twisted import MetricsResource
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor

with open("logging-config.yaml", "r") as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

root = Resource()

present_power_reading_gauge = Gauge(
    "current_power_usage",
    "Gauge for current power usage",
    ["power_mode", "power_status"],
)
fan_gauge = Gauge(
    "fan_speed_percent_gauge", "Gauge for current fan speed percentage", ["fan_name"]
)
current_temperature_gauge = Gauge(
    "current_temperature_gauge", "Gauge for current temperature", ["location",]
)
critical_temperature_gauge = Gauge(
    "critical_temperature_gauge", "Gauge for critical temperature", ["location",]
)
caution_temperature_gauge = Gauge(
    "caution_temperature_gauge", "Gauge for caution temperature", ["location",]
)


class ILOMetrics(Resource):
    isLeaf = True

    def render_GET(self, request):
        logger.info("Request processing started")
        hostname = (request.args[b"hostname"][0]).decode("utf-8")
        port = int(request.args[b"port"][0])
        username = (request.args[b"username"][0]).decode("utf-8")
        password = (request.args[b"password"][0]).decode("utf-8")
        logger.info(f"Initializing ILO with : {hostname} {port} {username} {password}")
        ilo_client = Ilo(
            hostname=hostname, port=port, login=username, password=password
        )
        # ILO was reporting stale metrics when the server turns off. Doing this to prevent that.
        if ilo_client.get_host_power_status() != "OFF":
            power_status = ilo_client.get_host_power_saver_status()["host_power_saver"]
            logger.debug(f"Powered on Status: {power_status}")
            server_health = ilo_client.get_embedded_health()
            present_power_reading_str = server_health["power_supply_summary"][
                "present_power_reading"
            ]
            logger.debug(f"Present power usage : {present_power_reading_str}")
            power_mode = server_health["power_supply_summary"]["high_efficiency_mode"]
            logger.debug(f"Power mode : {power_mode}")
            present_power_reading = present_power_reading_str.replace("Watts", "").strip()
            present_power_reading_gauge.labels(power_mode, power_status).set(
                present_power_reading
            )
            for (fan_name, fan_status) in server_health["fans"].items():
                logger.debug(f"Fan name : {fan_name} , data: {fan_status}")
                fan_speed_percentage = fan_status["speed"][0]
                fan_gauge.labels(fan_name).set(fan_speed_percentage)
            for (label, temperature_data) in server_health["temperature"].items():
                logger.debug(f"Temperature Label : {label} , data: {temperature_data}")
                location = temperature_data["location"]
                currentreading = temperature_data["currentreading"]
                caution = temperature_data["caution"]
                critical = temperature_data["critical"]
                if currentreading != "N/A":
                    current_temperature_gauge.labels(location).set(currentreading[0])
                if caution != "N/A":
                    caution_temperature_gauge.labels(location).set(caution[0])
                if critical != "N/A":
                    critical_temperature_gauge.labels(location).set(critical[0])
            logger.info("Request processing finished")
            return MetricsResource().render_GET(request)
        else:
            present_power_reading_gauge._metrics.clear()
            fan_gauge._metrics.clear()
            current_temperature_gauge._metrics.clear()
            critical_temperature_gauge._metrics.clear()
            caution_temperature_gauge._metrics.clear()
            request.setResponseCode(500)
            return "Internal Server Error"

if __name__ == "__main__":
    root.putChild(b"metrics", ILOMetrics())
    factory = Site(root)
    reactor.listenTCP(8080, factory)
    reactor.run()