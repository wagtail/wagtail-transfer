# How It Works

## ID Mapping

When transferring content between Wagtail instances, it's important to keep track of previously
imported content: which models on the source site correspond to which on the destination site. Doing so
means that when a model is re-imported, the version on the destination site can be updated, rather
than recreated.

However, the local ids aren't guaranteed to be the same between source and destination sites, so can't be used directly.
Instead, when a model is imported for the first time, Wagtail Transfer creates an instance
of IDMapping: a model which maps a local id and model class to a unique ID (UID). This IDMapping maps source and
destination site local ids to the same UID, which allows Wagtail Transfer to identify re-imported content.

## Finding References

When importing a model, Wagtail Transfer identifies other models it refers to: for instance, via
ForeignKeys, or as references in rich text. It must then decide whether these objects should be:
* Located (and if they don't exist on the destination site, the link broken) 
* Imported (if they don't exist, and otherwise left alone)
* Pulled in and updated from the source site.

This behaviour is configurable on a per-model basis:

ADD CONFIG LINK OR SECTION HERE 
