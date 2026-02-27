# My document

This is a MyST document with [@smith2020] references.

```{python}
#| code-fold: true

import numpy as np
x = np.linspace(0, 1, 100)
```

![My figure caption.](images/plot.png){#fig-plot width="80%"}

As shown in @fig-plot, the result from @eq-energy is clear.

$$
E = mc^2
$$ {#eq-energy}

::: {.callout-note}
This is an important note.
:::

::: {.callout-warning}
Be careful with this.
:::


The value is `{python} compute_value()`.

See [methods](methods.qmd) for more.

