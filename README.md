# slimbb

*[djangobb][djangobb] with cruft removed.*

slimbb is a fork of [djangobb][djangobb] which, at the time of the fork, was slowly falling into
abandon. To keep my own forum instance afloat and to minimize my own maintenance burden, I
proceeded to remove all the useless (to me) cruft that had accumulated in djangobb over the years.

That might seem petty, but all those cute features ended up amounting to significant complexity
(and thus maintenance burden).

This library will be kept in check, feature-wise. It will not go over the state of "like a
mailing list, but searchable and usable through a web browser". Everything else is cut off.


## Installation

Will be written soon. For now, you should follow djangobb's instructions. It's similar.

## Migrate from djangobb

To convert a djangobb forum into a slimbb one, copy the contents of the `migrate_from_djangobb`
folder into your current install's djangobb migrations folder. Then, run the migrations. This will,
among other things, rename all your tables to the `slimbb` prefix.

Then, uninstall djangobb and install slimbb and run `manage.py migrate --fake-initial`

Then, you'll need to rename your template overrides (if any) from `django_forum` to `slimbb`. By
that, I mean renaming the folder `templates/django_forum` to `templates/slimbb` in your own forum
project.

Then, you'll need to edit all those templates and replace all `djangobb` or `djangobb_forum`
references to `slimbb`.

You'll also need to replace your `DJANGOBB_*` settings with `SLIMBB_*`.

After that, you should be good to go.

[djangobb]: http://bitbucket.org/slav0nic/djangobb
