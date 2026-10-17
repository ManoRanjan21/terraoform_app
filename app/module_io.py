# Outputs from s3_us_east that are passed as variables into s3_eu_west_1.
# Add a dict here when the first module exposes a new output the second module needs.
# from_output  = terraform output name in s3_us_east/output.tf
# to_variable  = terraform variable name in s3_eu_west_1/variables.tf
# suffix       = optional string appended to the output value
#
# Example: API bucket_name dbx-bucket-testing
#   s3_name -> bucket_name becomes dbx-bucket-testing-module1

MODULE_OUTPUT_MAP = [
    {
        "from_output": "s3_name",
        "to_variable": "bucket_name",
        "suffix": "-module1",
    },
    # {
    #     "from_output": "s3_location",
    #     "to_variable": "source_region",
    #     "suffix": "",
    # },
]


def build_next_module_inputs(first_outputs: dict) -> dict:
    inputs = {}
    for rule in MODULE_OUTPUT_MAP:
        source = rule["from_output"]
        if source not in first_outputs:
            raise KeyError(
                "First module output '{0}' is not available to send to the second module".format(source)
            )
        value = first_outputs[source]
        suffix = rule.get("suffix") or ""
        if suffix:
            value = "{0}{1}".format(value, suffix)
        inputs[rule["to_variable"]] = value
    return inputs
