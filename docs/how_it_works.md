# How It Works

## ID Mapping

When transferring content between Wagtail instances, it's important to keep track of previously
imported content: which models on the source site correspond to which on the destination site. Doing so
means that when a model is re-imported, the version on the destination site can be updated, rather
than recreated.

However, the local ids aren't guaranteed to be the same between source and destination sites, so can't be used directly.
Instead, when a model is imported for the first time, Wagtail Transfer creates an instance
of `IDMapping`: a model which maps a local id and model class to a unique ID (UID). This `IDMapping` maps source and
destination site local ids to the same UID, which allows Wagtail Transfer to identify re-imported content.

It's also possible to identify models by their fields, rather than via `IDMapping`s. This can be accomplished using the
[`WAGTAILTRANSFER_LOOKUP_FIELDS`](settings.md) setting.

## Finding References

When importing a model, Wagtail Transfer identifies other models it refers to: for instance, via
`ForeignKeys`, or as references in rich text. Wagtail Transfer will attempt to recursively import unimported
referenced models, until encountering a model listed in [`WAGTAILTRANSFER_NO_FOLLOW_MODELS`](settings.md) (by default, `Page`).
At that point the reference will be broken if possible, but if the reference is required for import then the
referencing model will not be imported.

Non-`Page` models which already exist on both sites will not be updated unless they are listed in  [`WAGTAILTRANSFER_UPDATE_RELATED_MODELS`](settings.md). The exception here is if a Snippet model or an individual Snippet object is selected using the Snippet Chooser (rather than the Page Chooser). Then the selected model/object will be updated explicitly.
