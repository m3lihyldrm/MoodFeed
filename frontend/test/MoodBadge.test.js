import { describe, it, expect } from 'vitest';

describe('MoodBadge Emoji and Class Classifier', () => {
  const getMoodBadge = (label) => {
    const badges = {
      happy: { emoji: '😊', name: 'Mutlu', cls: 'badge-mood-happy' },
      sad: { emoji: '😢', name: 'Üzgün', cls: 'badge-mood-sad' },
      angry: { emoji: '😠', name: 'Öfkeli', cls: 'badge-mood-angry' },
      anxious: { emoji: '😰', name: 'Endişeli', cls: 'badge-mood-anxious' },
      neutral: { emoji: '😐', name: 'Nötr', cls: 'badge-mood-neutral' }
    };
    return badges[label] || badges.neutral;
  };

  it('classifies happy mood correctly', () => {
    const badge = getMoodBadge('happy');
    expect(badge.emoji).toBe('😊');
    expect(badge.cls).toBe('badge-mood-happy');
  });

  it('classifies sad mood correctly', () => {
    const badge = getMoodBadge('sad');
    expect(badge.emoji).toBe('😢');
    expect(badge.cls).toBe('badge-mood-sad');
  });

  it('defaults to neutral when unknown', () => {
    const badge = getMoodBadge('unknown');
    expect(badge.emoji).toBe('😐');
  });
});
