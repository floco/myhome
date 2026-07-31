<script lang="ts">
  import ScheduleEditor from "../../src/lib/components/ScheduleEditor.svelte";

  interface Props {
    initialFrequencyType?: string;
    initialFrequency?: number;
    initialFrequencyMetadata?: Record<string, unknown>;
    initialPeriodDays?: number;
  }
  let {
    initialFrequencyType = "interval",
    initialFrequency = 30,
    initialFrequencyMetadata = { unit: "days" },
    initialPeriodDays = 30,
  }: Props = $props();

  let frequencyType = $state(initialFrequencyType);
  let frequency = $state(initialFrequency);
  let frequencyMetadata = $state(initialFrequencyMetadata);
  let periodDays = $state(initialPeriodDays);
  let valid = $state(true);
</script>

<ScheduleEditor bind:frequencyType bind:frequency bind:frequencyMetadata bind:periodDays bind:valid />
<div class="state-dump">{JSON.stringify({ frequencyType, frequency, frequencyMetadata, periodDays, valid })}</div>
