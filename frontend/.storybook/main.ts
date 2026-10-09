import type { StorybookConfig } from '@storybook/react-vite'

const config: StorybookConfig = {
  stories: ['../src/**/*.mdx', '../src/**/*.stories.@(js|jsx|mjs|ts|tsx)'],
  // SB10: addon-essentials/addon-interactions merged into core; re-add
  // '@storybook/addon-docs' if MDX docs are introduced.
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
}

export default config
