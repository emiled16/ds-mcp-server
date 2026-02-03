# from mlflow.exceptions import MlflowException

# from src.data_science.snowflake_optional import Session, require_snowflake


# class DeploymentHelper:
#     """Provide naive UDF deployment management."""

#     _MLFLOW_MODEL_PREFIX = "MLFLOW$"

#     def __init__(self, session: Session) -> None:
#         require_snowflake()
#         self._session = session

#     @staticmethod
#     def normalize_name(name: str) -> str:
#         """Get normalized name for deployment.

#         Args:
#             name (str): User provided deployment name.

#         Returns:
#             str: Normalized deployent name with proper prefix.
#         """
#         if name.upper().startswith(DeploymentHelper._MLFLOW_MODEL_PREFIX):
#             return name.upper()

#         return f"{DeploymentHelper._MLFLOW_MODEL_PREFIX}{name.upper()}"

#     def get_deployment(self, name: str) -> str:
#         """Get deployment managed by this deployment plugin.

#         Args:
#             name (str): Name for the deployment.

#         Raises:
#             MlflowException: If there is more than one matching deployment.
#             MlflowException: If the deployment does not exist.

#         Returns:
#             str: Signature for the deployment.
#         """
#         res = self._session.sql(f"SHOW USER FUNCTIONS LIKE '{self.normalize_name(name)}%'").collect()
#         if len(res) == 0:
#             raise MlflowException(f"Deployment {name} does not exist.")
#         if len(res) > 1:
#             raise MlflowException(f"More than one deployment with name {name} exist.")
#         return self._function_signature(res[0].arguments)

#     def list_deployments(self) -> list[tuple[str, str]]:
#         """List all the deployments managed by the deployment plugin.

#         Returns
#             List[Tuple[str, str]]: (Name, Function signature) of the deployments.
#         """
#         res = []
#         qres = self._session.sql(f"SHOW USER FUNCTIONS LIKE '{self._MLFLOW_MODEL_PREFIX}%'").collect()
#         for func in qres:
#             res.append((func.name, self._function_signature(func.arguments)))
#         return res

#     def delete_deployment(self, name: str) -> None:
#         """Delete the deployment."""
#         try:
#             signature = self.get_deployment(self.normalize_name(name))
#         except Exception:
#             return
#         self._session.sql(f"DROP FUNCTION IF EXISTS {signature}").collect()

#     @staticmethod
#     def _function_signature(argument: str) -> str:
#         """Extract function signature from function arguments string.

#         Args:
#             argument (str): Function argument in form of
#                 `name(type1, type2..) RETURN typeN`

#         Returns:
#             str: Signature for the UDF function.
#         """
#         return argument[: argument.find(" RETURN")].rstrip()
