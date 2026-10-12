"""world_census: inventory every world, realm and island of a metaverse project.

Pipeline: sources.collect() -> model.build() -> report.{json,md,html,xlsx}.
Project-specific knowledge lives in a config (see config.py / DEFAULT_CONFIG), so
other projects can reuse the module by passing their own JSON config.
"""
__version__ = "0.1.0"
