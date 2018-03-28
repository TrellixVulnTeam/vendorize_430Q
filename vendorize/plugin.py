import click
import os


import vendorize.processor


class PluginError(click.ClickException):
    """Exception for any unrecoverable error in a plugin.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Plugin:
    def __init__(self, processor: vendorize.processor.Processor,
                 part: str, data: dict, source: str, copy: str) -> None:
        self.processor = processor
        self.part = part
        self.data = data
        self.source = source
        self.copy = copy

        self.part_dir = os.path.join(processor.project_folder, 'parts', part)

    def process(self):
        """The entry point called by the processor for each part.

        This needs to be implemented in the subclass to do the following:
          1. Fetch any plugin-specific sources that are not vendored.
          2. Prepare a branch for each such source.
          3. Modify data to point to vendored sources only.
        """
        raise NotImplementedError()

    def debug(self, message: str):
        """Log a message that is only visible if debugging is enabled.
        """
        self.processor.logger.debug(message)
