import { palette } from "@primevue/themes";
import { surfaces } from "@/presets/surfaces";
import { omit } from "@/util/obj";

export const defaultPrimaryColor = "#00ffbf";
export const customPrimaryPalette = palette(defaultPrimaryColor);

export const preset = {
  primitive: {
    borderRadius: {
      none: "0",
      xs: "0.125rem",
      sm: "0.25rem",
      md: "0.375rem",
      lg: "0.5rem",
      xl: "0.75rem",
    },
    ...omit(["robo"], surfaces),
  },
  semantic: {
    primary: {
      50: customPrimaryPalette["50"],
      100: customPrimaryPalette["100"],
      200: customPrimaryPalette["200"],
      300: customPrimaryPalette["300"],
      400: customPrimaryPalette["400"],
      500: customPrimaryPalette["500"],
      600: customPrimaryPalette["600"],
      700: customPrimaryPalette["700"],
      800: customPrimaryPalette["800"],
      900: customPrimaryPalette["900"],
      950: customPrimaryPalette["950"],
    },
    transitionDuration: "0.2s",
    focusRing: {
      width: "0.0625rem",
      style: "solid",
      color: "{primary.color}",
      offset: "0.125rem",
      shadow: "none",
    },
    disabledOpacity: "0.6",
    iconSize: "inherit",
    anchorGutter: "0.125rem",
    formField: {
      paddingY: "0.5rem",
      paddingX: "0.75rem",
      sm: {
        fontSize: "0.875rem",
        paddingX: "0.625rem",
        paddingY: "0.375rem",
      },
      lg: {
        fontSize: "1.125rem",
        paddingX: "0.875rem",
        paddingY: "0.625rem",
      },
      borderRadius: "{border.radius.md}",
      focusRing: {
        width: "0",
        style: "none",
        color: "transparent",
        offset: "0",
        shadow: "none",
      },
      transitionDuration: "{transition.duration}",
    },
    list: {
      padding: "0.25rem 0.25rem",
      gap: "0.125rem",
      header: {
        padding: "0.5rem 1rem 0.25rem 1rem",
      },
      option: {
        padding: "0.5rem 0.75rem",
        borderRadius: "{border.radius.sm}",
      },
      optionGroup: {
        padding: "0.5rem 0.75rem",
        fontWeight: "600",
      },
    },
    content: {
      borderRadius: "{border.radius.md}",
    },
    mask: {
      background: "rgba(0,0,0,0.4)",
      color: "{surface.200}",
    },
    navigation: {
      list: {
        padding: "0.25rem 0.25rem",
        gap: "0.125rem",
      },
      item: {
        padding: "0.5rem 0.75rem",
        borderRadius: "{border.radius.sm}",
        gap: "0.5rem",
      },
      submenuLabel: {
        padding: "0.5rem 0.75rem",
        fontWeight: "600",
      },
      submenuIcon: {
        size: "0.875rem",
      },
    },
    overlay: {
      select: {
        borderRadius: "{border.radius.md}",
        shadow:
          "0 0.25rem 0.375rem -0.0625rem rgba(0, 0, 0, 0.1), 0 0.125rem 0.25rem -0.125rem rgba(0, 0, 0, 0.1)",
      },
      popover: {
        borderRadius: "{border.radius.md}",
        padding: "0.75rem",
        shadow:
          "0 0.25rem 0.375rem -0.0625rem rgba(0, 0, 0, 0.1), 0 0.125rem 0.25rem -0.125rem rgba(0, 0, 0, 0.1)",
      },
      modal: {
        borderRadius: "{border.radius.xl}",
        padding: "1.25rem",
        shadow:
          "0 1.25rem 1.5625rem -0.3125rem rgba(0, 0, 0, 0.1), 0 0.5rem 0.625rem -0.375rem rgba(0, 0, 0, 0.1)",
      },
      navigation: {
        shadow:
          "0 0.25rem 0.375rem -0.0625rem rgba(0, 0, 0, 0.1), 0 0.125rem 0.25rem -0.125rem rgba(0, 0, 0, 0.1)",
      },
    },
    colorScheme: {
      light: {
        surface: {
          0: "#ffffff",
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
          950: "#020617",
        },
        primary: {
          color: "{primary.600}",
          contrastColor: "#ffffff",
          hoverColor: "{primary.700}",
          activeColor: "{primary.800}",
        },
        highlight: {
          background: "{primary.50}",
          focusBackground: "{primary.100}",
          color: "{primary.700}",
          focusColor: "{primary.800}",
        },
        mask: {
          background: "rgba(0,0,0,0.4)",
          color: "{surface.200}",
        },
        formField: {
          background: "{surface.100}",
          disabledBackground: "{surface.300}",
          filledBackground: "{surface.50}",
          filledHoverBackground: "{surface.50}",
          filledFocusBackground: "{surface.50}",
          borderColor: "{surface.800}",
          hoverBorderColor: "{surface.400}",
          focusBorderColor: "{primary.color}",
          invalidBorderColor: "{red.400}",
          color: "{surface.800}",
          disabledColor: "{surface.500}",
          placeholderColor: "{surface.700}",
          invalidPlaceholderColor: "{red.600}",
          floatLabelColor: "{surface.500}",
          floatLabelFocusColor: "{primary.600}",
          floatLabelActiveColor: "{surface.500}",
          floatLabelInvalidColor: "{form.field.invalid.placeholder.color}",
          iconColor: "{surface.800}",
          shadow:
            "0 0 #0000, 0 0 #0000, 0 0.0625rem 0.125rem 0 rgba(18, 18, 23, 0.05)",
        },
        text: {
          color: "{surface.700}",
          hoverColor: "{surface.800}",
          mutedColor: "{surface.500}",
          hoverMutedColor: "{surface.600}",
        },
        content: {
          background: "{surface.100}",
          hoverBackground: "{surface.200}",
          borderColor: "{surface.300}",
          color: "{text.color}",
          hoverColor: "{text.hover.color}",
        },
        overlay: {
          select: {
            background: "{surface.0}",
            borderColor: "{surface.200}",
            color: "{text.color}",
          },
          popover: {
            background: "{surface.0}",
            borderColor: "{surface.200}",
            color: "{text.color}",
          },
          modal: {
            background: "{surface.100}",
            borderColor: "{surface.200}",
            color: "{text.color}",
          },
        },
        list: {
          option: {
            focusBackground: "{surface.100}",
            selectedBackground: "{highlight.background}",
            selectedFocusBackground: "{highlight.focus.background}",
            color: "{text.color}",
            focusColor: "{text.hover.color}",
            selectedColor: "{highlight.color}",
            selectedFocusColor: "{highlight.focus.color}",
            icon: {
              color: "{surface.400}",
              focusColor: "{surface.500}",
            },
          },
          optionGroup: {
            background: "transparent",
            color: "{text.muted.color}",
          },
        },
        navigation: {
          item: {
            focusBackground: "{surface.100}",
            activeBackground: "{surface.100}",
            color: "{text.color}",
            focusColor: "{text.hover.color}",
            activeColor: "{text.hover.color}",
            icon: {
              color: "{surface.400}",
              focusColor: "{surface.500}",
              activeColor: "{surface.500}",
            },
          },
          submenuLabel: {
            background: "transparent",
            color: "{text.muted.color}",
          },
          submenuIcon: {
            color: "{surface.400}",
            focusColor: "{surface.500}",
            activeColor: "{surface.500}",
          },
        },
      },
      dark: {
        surface: {
          0: "#ffffff",
          50: "#fafafa",
          100: "#f4f4f5",
          200: "#e4e4e7",
          300: "#d4d4d8",
          400: "#a1a1aa",
          500: "#71717a",
          600: "#52525b",
          700: "#3f3f46",
          800: "#27272a",
          900: "#18181b",
          950: "#09090b",
        },
        primary: {
          color: "{primary.500}",
          contrastColor: "{surface.900}",
          hoverColor: "{primary.300}",
          activeColor: "{primary.200}",
        },
        highlight: {
          background: "color-mix(in srgb, {primary.400}, transparent 84%)",
          focusBackground: "color-mix(in srgb, {primary.400}, transparent 76%)",
          color: "rgba(255,255,255,.87)",
          focusColor: "rgba(255,255,255,.87)",
        },
        formField: {
          background: "{surface.950}",
          disabledBackground: "{surface.700}",
          filledBackground: "{surface.800}",
          filledHoverBackground: "{surface.800}",
          filledFocusBackground: "{surface.800}",
          borderColor: "{surface.600}",
          hoverBorderColor: "{surface.500}",
          focusBorderColor: "{primary.color}",
          invalidBorderColor: "{red.300}",
          color: "{surface.0}",
          disabledColor: "{surface.400}",
          placeholderColor: "{surface.400}",
          invalidPlaceholderColor: "{red.400}",
          floatLabelColor: "{surface.400}",
          floatLabelFocusColor: "{primary.color}",
          floatLabelActiveColor: "{surface.400}",
          floatLabelInvalidColor: "{form.field.invalid.placeholder.color}",
          iconColor: "{surface.400}",
          shadow: "0 0 #0000, 0 0 #0000, 0 1px 2px 0 rgba(18, 18, 23, 0.05)",
        },
        text: {
          color: "{surface.0}",
          hoverColor: "{surface.0}",
          mutedColor: "{surface.400}",
          hoverMutedColor: "{surface.300}",
        },
        content: {
          background: "{surface.900}",
          hoverBackground: "{surface.800}",
          borderColor: "{surface.700}",
          color: "{text.color}",
          hoverColor: "{text.hover.color}",
        },
        overlay: {
          select: {
            background: "{surface.900}",
            borderColor: "{surface.700}",
            color: "{text.color}",
          },
          popover: {
            background: "{surface.900}",
            borderColor: "{surface.700}",
            color: "{text.color}",
          },
          modal: {
            background: "{surface.900}",
            borderColor: "{surface.700}",
            color: "{text.color}",
          },
        },
        list: {
          option: {
            focusBackground: "{surface.800}",
            selectedBackground: "{highlight.background}",
            selectedFocusBackground: "{highlight.focus.background}",
            color: "{text.color}",
            focusColor: "{text.hover.color}",
            selectedColor: "{highlight.color}",
            selectedFocusColor: "{highlight.focus.color}",
            icon: {
              color: "{surface.500}",
              focusColor: "{surface.400}",
            },
          },
          optionGroup: {
            background: "transparent",
            color: "{text.muted.color}",
          },
        },
        navigation: {
          item: {
            focusBackground: "{surface.800}",
            activeBackground: "{surface.800}",
            color: "{text.color}",
            focusColor: "{text.hover.color}",
            activeColor: "{text.hover.color}",
            icon: {
              color: "{surface.500}",
              focusColor: "{surface.400}",
              activeColor: "{surface.400}",
            },
          },
          submenuLabel: {
            background: "transparent",
            color: "{text.muted.color}",
          },
          submenuIcon: {
            color: "{surface.500}",
            focusColor: "{surface.400}",
            activeColor: "{surface.400}",
          },
        },
      },
    },
  },
  components: {
    inputtext: {
      paddingY: "0.5rem",
      paddingX: "0.75rem",
    },
    select: {
      dropdownWidth: "1.25rem",
      paddingY: "0.5rem 0rem",
      paddingX: "0.5rem 0.75rem",
    },
    treeselect: {
      dropdownWidth: "1.25rem",
      paddingY: "0.5rem 0.5rem",
      paddingX: "0.5rem 0.75rem",
    },
    fieldset: {
      legend: {},
    },
    progressbar: {
      height: "0.3rem",
    },
  },
};
