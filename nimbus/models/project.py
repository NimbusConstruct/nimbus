class Project:

    def __init__(self, data: dict):
        self.app_type = data.get("app_type")
        self.auth_required = data.get("auth_required", False)
        self.user_scale = data.get("user_scale", "low")
        self.integrations = data.get("integrations", [])
        self.real_time = data.get("real_time", False)
        self.sensitive_data = data.get("sensitive_data", False)
        self.compliance = data.get("compliance", False)
        self.deployment = data.get("deployment", "container")

    def to_dict(self):
        return self.__dict__