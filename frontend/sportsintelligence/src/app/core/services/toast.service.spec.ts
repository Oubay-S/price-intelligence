import { TestBed } from '@angular/core/testing';

import { ToastService } from './toast.service';

describe('ToastService', () => {
  let service: ToastService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ToastService);
  });

  it('starts with no toasts', () => {
    expect(service.toasts().length).toBe(0);
  });

  it('pushes a success toast (ttl 0 = no auto-dismiss timer)', () => {
    service.success('Saved', 0);
    const list = service.toasts();
    expect(list.length).toBe(1);
    expect(list[0].kind).toBe('success');
    expect(list[0].message).toBe('Saved');
  });

  it('assigns each toast a unique id', () => {
    service.info('one', 0);
    service.error('two', 0);
    const [a, b] = service.toasts();
    expect(a.id).not.toBe(b.id);
  });

  it('removes a toast by id on dismiss', () => {
    service.error('boom', 0);
    const id = service.toasts()[0].id;
    service.dismiss(id);
    expect(service.toasts().length).toBe(0);
  });
});
